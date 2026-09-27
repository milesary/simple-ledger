"""Initial SimpleLedger schema.

Revision ID: 20260926_0001
Revises:
Create Date: 2026-09-26
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260926_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    columns = sa.inspect(op.get_bind()).get_columns(table_name)
    return column_name in {column["name"] for column in columns}


def _create_index_if_missing(
    name: str,
    table_name: str,
    columns: list[str],
    *,
    unique: bool = False,
) -> None:
    indexes = sa.inspect(op.get_bind()).get_indexes(table_name)
    if name not in {index["name"] for index in indexes}:
        op.create_index(name, table_name, columns, unique=unique)


def upgrade() -> None:
    """Create the current schema or upgrade an existing pre-Alembic database."""
    if not _has_table("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("email", sa.String(length=254), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=True),
            sa.Column("is_admin", sa.Boolean(), server_default="0", nullable=False),
            sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("last_login_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    else:
        if not _has_column("users", "password_hash"):
            op.add_column("users", sa.Column("password_hash", sa.String(length=255)))
        if not _has_column("users", "is_admin"):
            op.add_column(
                "users",
                sa.Column("is_admin", sa.Boolean(), server_default="0", nullable=False),
            )
        if not _has_column("users", "is_active"):
            op.add_column(
                "users",
                sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
            )

    _create_index_if_missing("ix_users_email", "users", ["email"], unique=True)

    if not _has_table("login_codes"):
        op.create_table(
            "login_codes",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("email", sa.String(length=254), nullable=False),
            sa.Column("code_hash", sa.String(length=64), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("attempts", sa.Integer(), nullable=False),
            sa.Column("consumed_at", sa.DateTime(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    _create_index_if_missing("ix_login_codes_email", "login_codes", ["email"])
    _create_index_if_missing(
        "ix_login_codes_email_created_at",
        "login_codes",
        ["email", "created_at"],
    )

    if not _has_table("categories"):
        op.create_table(
            "categories",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=50), nullable=False),
            sa.Column("type", sa.String(length=10), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table("transactions"):
        op.create_table(
            "transactions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("type", sa.String(length=10), nullable=False),
            sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column("category_id", sa.Integer(), nullable=False),
            sa.Column("occurred_on", sa.Date(), nullable=False),
            sa.Column("payment_method", sa.String(length=20), nullable=True),
            sa.Column("note", sa.String(length=200), nullable=True),
            sa.Column("import_hash", sa.String(length=64), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    _create_index_if_missing(
        "ix_tx_user_occurred",
        "transactions",
        ["user_id", "occurred_on"],
    )
    _create_index_if_missing(
        "ix_tx_user_category",
        "transactions",
        ["user_id", "category_id"],
    )
    _create_index_if_missing("ix_tx_user_type", "transactions", ["user_id", "type"])
    _create_index_if_missing(
        "ix_tx_user_import_hash",
        "transactions",
        ["user_id", "import_hash"],
    )

    if not _has_table("budgets"):
        op.create_table(
            "budgets",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("month", sa.String(length=7), nullable=False),
            sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "month", name="uq_budget_user_month"),
        )


def downgrade() -> None:
    """Drop all application tables."""
    for table_name in (
        "budgets",
        "transactions",
        "categories",
        "login_codes",
        "users",
    ):
        if _has_table(table_name):
            op.drop_table(table_name)
