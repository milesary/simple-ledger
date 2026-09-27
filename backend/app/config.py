"""配置管理：从环境变量读取，未设置时使用开发默认值。"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Backend 根目录及整个项目根目录。
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

# 直接导入配置时也能加载 backend/.env。
load_dotenv(BASE_DIR / ".env")

# Vue 生产构建目录。
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"


def _env_bool(name: str, default: bool) -> bool:
    """读取布尔环境变量，接受常见的 true/false 写法。"""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: str) -> list[str]:
    """读取逗号分隔的环境变量列表。"""
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


# 应用配置
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-prod")
DEFAULT_DATABASE_URL = (
    "mysql+pymysql://root:change-me@127.0.0.1:3306/simple_ledger?charset=utf8mb4"
)
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

# 允许携带 Session Cookie 的浏览器来源
CORS_ORIGINS = _env_list(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)

# 允许登录的邮箱域名
ALLOWED_EMAIL_DOMAINS = _env_list("ALLOWED_EMAIL_DOMAINS", "qq.com")

# 验证码规则
CODE_EXPIRE_MINUTES = int(os.getenv("CODE_EXPIRE_MINUTES", "5"))
CODE_SEND_INTERVAL_SECONDS = int(os.getenv("CODE_SEND_INTERVAL_SECONDS", "60"))
CODE_MAX_ATTEMPTS = int(os.getenv("CODE_MAX_ATTEMPTS", "5"))
CODE_SEND_MAX_PER_HOUR = int(os.getenv("CODE_SEND_MAX_PER_HOUR", "5"))

# 邮件配置
MAIL_HOST = os.getenv("MAIL_HOST", "smtp.qq.com")
MAIL_PORT = int(os.getenv("MAIL_PORT", "465"))
MAIL_USERNAME = os.getenv("MAIL_USERNAME", "")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")
MAIL_FROM = os.getenv("MAIL_FROM", "")
MAIL_USE_TLS = _env_bool("MAIL_USE_TLS", True)
MAIL_DEV_MODE = _env_bool("MAIL_DEV_MODE", True)

# Session
SESSION_HTTPS_ONLY = _env_bool("SESSION_HTTPS_ONLY", APP_ENV == "production")
SESSION_MAX_AGE_SECONDS = int(os.getenv("SESSION_MAX_AGE_SECONDS", "1209600"))

# 文件上传
MAX_UPLOAD_SIZE_BYTES = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(10 * 1024 * 1024)))

# 分页
PAGE_SIZE = int(os.getenv("PAGE_SIZE", "20"))

# 初始管理员：首次启动时自动创建或补齐管理员权限
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip().lower()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")


def validate_settings(
    app_env: str = APP_ENV,
    secret_key: str = SECRET_KEY,
    mail_dev_mode: bool = MAIL_DEV_MODE,
) -> None:
    """拒绝不安全的生产配置，避免带着开发默认值上线。"""
    if app_env not in {"development", "testing", "production"}:
        raise RuntimeError("APP_ENV 必须是 development、testing 或 production")
    if app_env != "production":
        return
    if secret_key == "dev-secret-change-in-prod" or len(secret_key) < 32:
        raise RuntimeError("生产环境必须配置至少 32 位的随机 SECRET_KEY")
    if mail_dev_mode:
        raise RuntimeError("生产环境必须设置 MAIL_DEV_MODE=false")


validate_settings()
