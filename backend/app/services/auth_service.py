"""认证服务：验证码生成、发送频率限制、验证与用户创建。"""
import math
from datetime import timedelta
from typing import Optional

from aiosmtplib.errors import (
    SMTPAuthenticationError,
    SMTPConnectError,
    SMTPServerDisconnected,
)
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.config import (
    CODE_EXPIRE_MINUTES,
    CODE_MAX_ATTEMPTS,
    CODE_SEND_INTERVAL_SECONDS,
    CODE_SEND_MAX_PER_HOUR,
    LOGIN_LOCKOUT_MINUTES,
    LOGIN_MAX_ATTEMPTS,
)
from app.models import LoginAttempt, LoginCode, User
from app.security import (
    generate_login_code,
    hash_code,
    hash_password,
    is_allowed_email_domain,
    normalize_email,
    verify_code,
    verify_password,
)
from app.services.mail_service import mail_service
from app.utils import utc_now


class AuthError(Exception):
    """认证流程中的业务异常，由 router 捕获并转为用户提示。"""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class AuthService:
    """登录验证码与用户管理服务。"""

    def __init__(self, db: Session) -> None:
        self.db = db

    def _invalidate_old_codes(self, email: str) -> None:
        """将该邮箱所有未消费的旧验证码标记为已消费（新验证码生成后旧码失效）。"""
        now = utc_now()
        stmt = select(LoginCode).where(
            LoginCode.email == email,
            LoginCode.consumed_at.is_(None),
        )
        for code in self.db.scalars(stmt):
            code.consumed_at = now

    def _validate_password(self, password: str) -> None:
        """校验注册密码强度。"""
        if len(password) < 8 or len(password) > 20:
            raise AuthError("密码长度必须为 8-20 位")
        has_digit = any(char.isdigit() for char in password)
        has_letter = any(char.isalpha() for char in password)
        if not has_digit or not has_letter:
            raise AuthError("密码必须同时包含字母和数字")

    def register(self, email: str, password: str) -> User:
        """注册新用户，账号以邮箱唯一标识。"""
        email = normalize_email(email)
        if not is_allowed_email_domain(email):
            raise AuthError("仅支持 QQ 邮箱（QQ号@qq.com）")
        self._validate_password(password)

        exists = self.db.scalar(select(User).where(User.email == email))
        if exists is not None:
            raise AuthError("该邮箱已注册，请直接登录")

        user = User(
            email=email,
            password_hash=hash_password(password),
            is_admin=False,
            is_active=True,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def _get_attempt(self, email: str) -> Optional[LoginAttempt]:
        """读取该邮箱的失败计数行。"""
        return self.db.scalar(select(LoginAttempt).where(LoginAttempt.email == email))

    def _check_login_lock(self, email: str) -> None:
        """在验证密码前检查锁定状态，命中则直接拒绝。"""
        attempt = self._get_attempt(email)
        if attempt is None or attempt.locked_until is None:
            return

        now = utc_now()
        if attempt.locked_until <= now:
            # 锁定已过期，清理计数，让本次登录按正常流程继续。
            self.db.delete(attempt)
            self.db.commit()
            return

        remaining_seconds = (attempt.locked_until - now).total_seconds()
        # 用 ceil 而不是 floor+1：刚锁定时剩余 14 分 59.9 秒应显示 15 分钟而不是 16。
        remaining_minutes = max(1, math.ceil(remaining_seconds / 60))
        raise AuthError(
            f"密码错误次数过多，账号已锁定，请在 {remaining_minutes} 分钟后重试"
        )

    def _record_failed_login(self, email: str) -> None:
        """记录一次密码失败，达到上限时写入锁定时间。"""
        now = utc_now()
        attempt = self._get_attempt(email)
        if attempt is None:
            attempt = LoginAttempt(
                email=email,
                failed_count=0,
                window_started_at=now,
                last_failed_at=now,
            )
            self.db.add(attempt)

        window_seconds = LOGIN_LOCKOUT_MINUTES * 60
        window_expired = (
            attempt.window_started_at is not None
            and (now - attempt.window_started_at).total_seconds() > window_seconds
        )
        if window_expired:
            attempt.failed_count = 0
            attempt.window_started_at = now

        attempt.failed_count += 1
        attempt.last_failed_at = now

        if attempt.failed_count >= LOGIN_MAX_ATTEMPTS:
            # 归整到整秒再入库：MySQL DATETIME 会丢弃微秒，若写入带微秒的值再读回，
            # 剩余时长会比配置值略大（例如 900.4 秒），向上取整就会多报一分钟。
            locked_until = (now + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)).replace(
                microsecond=0
            )
            attempt.locked_until = locked_until

        self.db.commit()

    def _clear_failed_logins(self, email: str) -> None:
        """登录成功后清除该邮箱的失败计数。"""
        attempt = self._get_attempt(email)
        if attempt is not None:
            self.db.delete(attempt)
            self.db.commit()

    def login_with_password(self, email: str, password: str) -> User:
        """使用邮箱和密码登录；连续失败达到上限后按邮箱临时锁定。"""
        email = normalize_email(email)
        user = self.db.scalar(select(User).where(User.email == email))

        self._check_login_lock(email)

        if user is None:
            self._record_failed_login(email)
            raise AuthError("该账号不存在，请先注册")
        if not user.is_active:
            raise AuthError("该账号已被禁用，请联系管理员")
        if not user.password_hash:
            raise AuthError("该账号未设置密码，请使用验证码登录")
        if not verify_password(password, user.password_hash):
            self._record_failed_login(email)
            attempt = self._get_attempt(email)
            if attempt is not None and attempt.locked_until is not None:
                raise AuthError(
                    f"密码错误次数过多，账号已锁定 {LOGIN_LOCKOUT_MINUTES} 分钟"
                )
            raise AuthError("密码错误")

        self._clear_failed_logins(email)
        user.last_login_at = utc_now()
        self.db.commit()
        self.db.refresh(user)
        return user

    def request_login_code(self, email: str) -> None:
        """请求发送登录验证码：校验邮箱、频率限制、生成并发送。"""
        email = normalize_email(email)
        if not is_allowed_email_domain(email):
            raise AuthError("仅支持 QQ 邮箱（QQ号@qq.com）")

        user = self.db.scalar(select(User).where(User.email == email))
        if user is None:
            raise AuthError("该账号不存在，请先注册")
        if not user.is_active:
            raise AuthError("该账号已被禁用，请联系管理员")

        now = utc_now()

        # 60 秒内不能重复发送。历史数据可能带有非 UTC 的 created_at，
        # 这里把负的间隔（说明记录时间在未来）视为 0，避免误判为"刚刚发过"而长时间拒绝重发。
        recent = self.db.scalar(
            select(LoginCode)
            .where(LoginCode.email == email)
            .order_by(desc(LoginCode.created_at))
            .limit(1)
        )
        if recent and recent.created_at is not None:
            elapsed = max(0.0, (now - recent.created_at).total_seconds())
            if elapsed < CODE_SEND_INTERVAL_SECONDS:
                raise AuthError("验证码发送过于频繁，请稍后再试")

        # 1 小时内最多发送 N 次
        one_hour_ago = now - timedelta(hours=1)
        recent_count = self.db.scalar(
            select(func.count()).select_from(LoginCode).where(
                LoginCode.email == email,
                LoginCode.created_at >= one_hour_ago,
                LoginCode.created_at <= now,
            )
        ) or 0
        if recent_count >= CODE_SEND_MAX_PER_HOUR:
            raise AuthError("发送次数过多，请稍后再试")

        # 使旧验证码失效
        self._invalidate_old_codes(email)

        # 生成新验证码并保存哈希
        code = generate_login_code()
        code_hash = hash_code(email, code)
        login_code = LoginCode(
            email=email,
            code_hash=code_hash,
            expires_at=now + timedelta(minutes=CODE_EXPIRE_MINUTES),
            attempts=0,
        )
        self.db.add(login_code)
        self.db.commit()

        # 发送邮件（失败时回滚验证码记录）
        try:
            import asyncio

            asyncio.run(mail_service.send_login_code(email, code))
        except SMTPAuthenticationError as exc:
            self.db.delete(login_code)
            self.db.commit()
            raise AuthError("QQ 邮箱 SMTP 授权失败，请重新生成并填写授权码") from exc
        except SMTPServerDisconnected as exc:
            self.db.delete(login_code)
            self.db.commit()
            raise AuthError(
                "QQ 邮箱拒绝了 SMTP 登录，请确认已开启 SMTP 服务并使用最新授权码"
            ) from exc
        except SMTPConnectError as exc:
            self.db.delete(login_code)
            self.db.commit()
            raise AuthError("无法连接 QQ 邮箱 SMTP，请检查 MAIL_HOST 和 MAIL_PORT") from exc
        except Exception as exc:
            self.db.delete(login_code)
            self.db.commit()
            raise AuthError(f"邮件发送失败：{exc}") from exc

    def verify_login_code(self, email: str, code: str) -> User:
        """验证验证码，成功则创建或返回用户，并标记验证码已消费。"""
        email = normalize_email(email)
        now = utc_now()

        # 取该邮箱最新一条未消费的验证码
        login_code = self.db.scalar(
            select(LoginCode)
            .where(
                LoginCode.email == email,
                LoginCode.consumed_at.is_(None),
            )
            .order_by(desc(LoginCode.created_at))
            .limit(1)
        )

        if login_code is None:
            raise AuthError("请先获取验证码")
        if login_code.expires_at < now:
            raise AuthError("验证码已过期，请重新获取")
        if login_code.attempts >= CODE_MAX_ATTEMPTS:
            login_code.consumed_at = now
            self.db.commit()
            raise AuthError("验证码错误次数过多，请重新获取")

        if not verify_code(email, code, login_code.code_hash):
            login_code.attempts += 1
            self.db.commit()
            raise AuthError("验证码错误")

        user = self.db.scalar(select(User).where(User.email == email))
        if user is None:
            raise AuthError("该账号不存在，请先注册")
        if not user.is_active:
            raise AuthError("该账号已被禁用，请联系管理员")

        # 验证成功：标记已消费
        login_code.consumed_at = now
        self.db.commit()

        # 只允许已注册用户登录，不再自动创建账号
        user.last_login_at = now
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_current_user(self, user_id: int) -> Optional[User]:
        """根据用户 ID 获取用户对象。"""
        return self.db.get(User, user_id)
