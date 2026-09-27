"""Use a portable generated key for budget uniqueness.

Revision ID: 20260926_0003
Revises: 20260926_0002
Create Date: 2026-09-26
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260926_0003"
down_revision: str | Sequence[str] | None = "20260926_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _index_names(table_name: str) -> set[str]:
    return {
        index["name"]
        for index in sa.inspect(op.get_bind()).get_indexes(table_name)
        if index["name"]
    }


def _column_names(table_name: str) -> set[str]:
    return {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns(table_name)
    }


def _drop_index_if_exists(name: str, table_name: str) -> None:
    if name in _index_names(table_name):
        op.drop_index(name, table_name=table_name)


def upgrade() -> None:
    """Add category_key and a unique constraint for total and category budgets."""
    _drop_index_if_exists("uq_budget_user_month_category", "budgets")
    _drop_index_if_exists("uq_budget_user_month_total", "budgets")

    if "category_key" in _column_names("budgets"):
        return

    dialect_name = op.get_bind().dialect.name
    if dialect_name == "sqlite":
        with op.batch_alter_table("budgets", recreate="always") as batch:
            batch.add_column(
                sa.Column(
                    "category_key",
                    sa.Integer(),
                    sa.Computed("COALESCE(category_id, 0)", persisted=True),
                    nullable=False,
                )
            )
            batch.create_unique_constraint(
                "uq_budget_user_month_category_key",
                ["user_id", "month", "category_key"],
            )
        return

    op.add_column(
        "budgets",
        sa.Column(
            "category_key",
            sa.Integer(),
            sa.Computed("COALESCE(category_id, 0)", persisted=True),
            nullable=False,
        ),
    )
    op.create_unique_constraint(
        "uq_budget_user_month_category_key",
        "budgets",
        ["user_id", "month", "category_key"],
    )


def downgrade() -> None:
    """Restore the previous partial indexes and remove category_key."""
    dialect_name = op.get_bind().dialect.name
    constraints = {
        constraint["name"]
        for constraint in sa.inspect(op.get_bind()).get_unique_constraints("budgets")
        if constraint["name"]
    }
    if "uq_budget_user_month_category_key" in constraints:
        op.drop_constraint(
            "uq_budget_user_month_category_key",
            "budgets",
            type_="unique",
        )

    if "category_key" in _column_names("budgets"):
        if dialect_name == "sqlite":
            with op.batch_alter_table("budgets", recreate="always") as batch:
                batch.drop_column("category_key")
        else:
            op.drop_column("budgets", "category_key")

    op.create_index(
        "uq_budget_user_month_total",
        "budgets",
        ["user_id", "month"],
        unique=True,
        sqlite_where=sa.text("category_id IS NULL"),
    )
    op.create_index(
        "uq_budget_user_month_category",
        "budgets",
        ["user_id", "month", "category_id"],
        unique=True,
        sqlite_where=sa.text("category_id IS NOT NULL"),
    )
