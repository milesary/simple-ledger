"""安全相关工具：邮箱标准化、域名校验、验证码 HMAC-SHA256 哈希。"""
import hashlib
import hmac
import secrets

from app.config import ALLOWED_EMAIL_DOMAINS, SECRET_KEY


def normalize_email(email: str) -> str:
    """标准化邮箱：去前后空格、转小写。"""
    return email.strip().lower()


def is_allowed_email_domain(email: str) -> bool:
    """校验邮箱域名是否在允许列表内。"""
    email = normalize_email(email)
    if "@" not in email:
        return False
    domain = email.rsplit("@", 1)[1]
    return domain in ALLOWED_EMAIL_DOMAINS


def generate_login_code() -> str:
    """生成 6 位数字验证码。"""
    return "".join(secrets.choice("0123456789") for _ in range(6))


def hash_code(email: str, code: str) -> str:
    """对邮箱+验证码做 HMAC-SHA256 哈希，返回 64 位十六进制字符串。"""
    message = f"{normalize_email(email)}:{code}".encode("utf-8")
    return hmac.new(SECRET_KEY.encode("utf-8"), message, hashlib.sha256).hexdigest()


def verify_code(email: str, code: str, code_hash: str) -> bool:
    """验证明文验证码与哈希是否匹配。"""
    return hmac.compare_digest(hash_code(email, code), code_hash)


def hash_password(password: str) -> str:
    """使用 PBKDF2-SHA256 生成带随机盐的密码哈希。"""
    salt = secrets.token_bytes(16)
    iterations = 310_000
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, password_hash: str | None) -> bool:
    """校验明文密码与 PBKDF2 哈希。"""
    if not password_hash:
        return False
    try:
        algorithm, iterations_text, salt_hex, digest_hex = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_text)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (TypeError, ValueError):
        return False

    actual = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(actual, expected)


def mask_email(email: str) -> str:
    """脱敏展示邮箱，用于日志或页面提示（不记录完整邮箱到日志）。"""
    email = normalize_email(email)
    if "@" not in email:
        return email
    local, domain = email.rsplit("@", 1)
    if len(local) <= 2:
        masked = local[0] + "*"
    else:
        masked = local[0] + "*" * (len(local) - 2) + local[-1]
    return f"{masked}@{domain}"
