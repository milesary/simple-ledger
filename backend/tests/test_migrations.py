"""Alembic 迁移测试。"""
from alembic import command
from sqlalchemy import create_engine, inspect

from app.migrations import get_alembic_config


def test_initial_migration_creates_schema(tmp_path):
    """空数据库可以通过 Alembic 创建完整表结构。"""
    database_path = tmp_path / "migration.db"
    database_url = f"sqlite:///{database_path.as_posix()}"

    command.upgrade(get_alembic_config(database_url), "head")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        assert {
            "alembic_version",
            "users",
            "login_codes",
            "categories",
            "transactions",
            "budgets",
            "accounts",
            "transfers",
            "recurring_transactions",
        }.issubset(set(inspector.get_table_names()))
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        assert {"password_hash", "is_admin", "is_active"}.issubset(user_columns)
        transaction_columns = {
            column["name"] for column in inspector.get_columns("transactions")
        }
        budget_columns = {
            column["name"] for column in inspector.get_columns("budgets")
        }
        assert "account_id" in transaction_columns
        assert {"category_id", "category_key"}.issubset(budget_columns)
        budget_constraints = {
            constraint["name"]
            for constraint in inspector.get_unique_constraints("budgets")
            if constraint["name"]
        }
        assert "uq_budget_user_month_category_key" in budget_constraints
    finally:
        engine.dispose()
