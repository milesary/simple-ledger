"""Alembic 迁移入口，供 CLI 和应用启动流程共用。"""
from alembic import command
from alembic.config import Config

from app.config import BASE_DIR, DATABASE_URL


def get_alembic_config(database_url: str | None = None) -> Config:
    """构造 Alembic 配置，并覆盖当前运行环境的数据库地址。"""
    config = Config(str(BASE_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BASE_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", (database_url or DATABASE_URL).replace("%", "%%"))
    return config


def upgrade_database(database_url: str | None = None) -> None:
    """将数据库升级到最新版本。"""
    command.upgrade(get_alembic_config(database_url), "head")
