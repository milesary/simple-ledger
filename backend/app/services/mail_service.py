"""邮件发送服务：通过 QQ 邮箱 SMTP 发送验证码。"""
import logging
from email.message import EmailMessage

import aiosmtplib

from app.config import (
    MAIL_DEV_MODE,
    MAIL_FROM,
    MAIL_HOST,
    MAIL_PASSWORD,
    MAIL_PORT,
    MAIL_USE_TLS,
    MAIL_USERNAME,
)
from app.security import mask_email

logger = logging.getLogger(__name__)


class MailService:
    """邮件服务，封装 QQ 邮箱 SMTP 发送逻辑。"""

    def __init__(self) -> None:
        self.host = MAIL_HOST
        self.port = MAIL_PORT
        self.username = MAIL_USERNAME
        self.password = MAIL_PASSWORD
        self.use_tls = MAIL_USE_TLS
        self.from_addr = MAIL_FROM or MAIL_USERNAME

    async def send_login_code(self, email: str, code: str) -> None:
        """发送登录验证码邮件。开发模式下打印到日志，不真实发送。"""
        subject = "【简账】你的登录验证码"
        body = (
            f"你好，\n\n"
            f"你的简账登录验证码是：{code}\n\n"
            f"验证码 5 分钟内有效，请勿泄露给他人。\n\n"
            f"—— 简账 SimpleLedger"
        )

        if MAIL_DEV_MODE:
            # 开发模式：将验证码打印到日志，方便本地测试
            logger.info("【DEV MODE】验证码已发送至 %s: %s", mask_email(email), code)
            return

        if not self.username or not self.password:
            raise RuntimeError("邮件服务未配置 MAIL_USERNAME / MAIL_PASSWORD")

        message = EmailMessage()
        message["From"] = self.from_addr
        message["To"] = email
        message["Subject"] = subject
        message.set_content(body)

        await aiosmtplib.send(
            message,
            hostname=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            use_tls=self.use_tls,
        )
        logger.info("验证码邮件已发送至 %s", mask_email(email))


# 全局单例
mail_service = MailService()
