"""Copy the current SimpleLedger SQLite data into MySQL."""
import argparse
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.engine import make_url

from app import models  # noqa: F401
from app.config import DATABASE_URL
from app.database import Base
from app.migrations import upgrade_database

TABLE_ORDER = (
    "users",
    "categories",
    "accounts",
    "login_codes",
    "transactions",
    "transfers",
    "recurring_transactions",
    "budgets",
)


def _table_names() -> list[str]:
    return [name for name in TABLE_ORDER if name in Base.metadata.tables]


def _target_is_empty(connection: sa.Connection, table_names: list[str]) -> bool:
    return all(
        connection.scalar(sa.select(sa.func.count()).select_from(Base.metadata.tables[name]))
        == 0
        for name in table_names
    )


def _clear_target(connection: sa.Connection, table_names: list[str]) -> None:
    for table_name in reversed(table_names):
        connection.execute(sa.delete(Base.metadata.tables[table_name]))


def copy_database(sqlite_path: Path, mysql_url: str, replace: bool) -> dict[str, int]:
    """Copy all rows while preserving numeric primary keys."""
    if not sqlite_path.is_file():
        raise FileNotFoundError(f"SQLite 数据库不存在: {sqlite_path}")

    parsed_url = make_url(mysql_url)
    if not parsed_url.drivername.startswith("mysql"):
        raise ValueError("目标 DATABASE_URL 必须是 MySQL 连接串")

    upgrade_database(mysql_url)

    source_engine = sa.create_engine(f"sqlite:///{sqlite_path.as_posix()}")
    target_engine = sa.create_engine(mysql_url, pool_pre_ping=True)
    table_names = _table_names()
    copied: dict[str, int] = {}

    try:
        with target_engine.connect() as target_connection:
            if not _target_is_empty(target_connection, table_names):
                if not replace:
                    raise RuntimeError("目标 MySQL 数据库非空；如需覆盖请传入 --replace")
                target_connection.execute(sa.text("SET FOREIGN_KEY_CHECKS=0"))
                _clear_target(target_connection, table_names)
                target_connection.execute(sa.text("SET FOREIGN_KEY_CHECKS=1"))
                target_connection.commit()

        with source_engine.connect() as source_connection, target_engine.begin() as target:
            for table_name in table_names:
                table = Base.metadata.tables[table_name]
                copy_columns = [
                    column
                    for column in table.columns
                    if column.computed is None
                ]
                rows = source_connection.execute(sa.select(*copy_columns)).mappings().all()
                values = [dict(row) for row in rows]
                if values:
                    target.execute(table.insert(), values)
                copied[table_name] = len(values)
    finally:
        source_engine.dispose()
        target_engine.dispose()

    return copied


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sqlite",
        type=Path,
        required=True,
        help="源 SQLite 文件路径",
    )
    parser.add_argument(
        "--mysql-url",
        default=DATABASE_URL,
        help="目标 MySQL SQLAlchemy 连接串",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="目标非空时清空已有业务数据后重新导入",
    )
    args = parser.parse_args()

    copied = copy_database(args.sqlite, args.mysql_url, args.replace)
    for table_name, count in copied.items():
        print(f"{table_name}: {count}")


if __name__ == "__main__":
    main()
