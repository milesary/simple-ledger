"""应用通用工具。"""
from datetime import UTC, datetime


def utc_now() -> datetime:
    """返回适合当前无时区数据库列使用的 UTC 时间。"""
    return datetime.now(UTC).replace(tzinfo=None)
