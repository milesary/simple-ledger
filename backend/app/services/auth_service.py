"""认证服务：验证码生成、发送频率限制、验证与用户创建。"""
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
)
from app.models import LoginCode, User
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

    def login_with_password(self, email: str, password: str) -> User:
        """使用邮箱和密码登录；不存在的账号必须提示先注册。"""
        email = normalize_email(email)
        user = self.db.scalar(select(User).where(User.email == email))
        if user is None:
            raise AuthError("该账号不存在，请先注册")
        if not user.is_active:
            raise AuthError("该账号已被禁用，请联系管理员")
        if not user.password_hash:
            raise AuthError("该账号未设置密码，请使用验证码登录")
        if not verify_password(password, user.password_hash):
            raise AuthError("密码错误")

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

        # 60 秒内不能重复发送
        recent = self.db.scalar(
            select(LoginCode)
            .where(LoginCode.email == email)
            .order_by(desc(LoginCode.created_at))
            .limit(1)
        )
        if recent and (now - recent.created_at).total_seconds() < CODE_SEND_INTERVAL_SECONDS:
            raise AuthError("验证码发送过于频繁，请稍后再试")

        # 1 小时内最多发送 N 次
        one_hour_ago = now - timedelta(hours=1)
        recent_count = self.db.scalar(
            select(func.count()).select_from(LoginCode).where(
                LoginCode.email == email,
                LoginCode.created_at >= one_hour_ago,
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
