"""Add accounts, transfers, recurring transactions, and category budgets.

Revision ID: 20260926_0002
Revises: 20260926_0001
Create Date: 2026-09-26
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260926_0002"
down_revision: str | Sequence[str] | None = "20260926_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create account-related tables and extend transactions and budgets."""
    dialect_name = op.get_bind().dialect.name

    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column(
            "initial_balance",
            sa.Numeric(precision=12, scale=2),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "is_archived",
            sa.Boolean(),
            server_default="0",
            nullable=False,
        ),
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
        sa.CheckConstraint(
            "type IN ('cash', 'bank', 'credit', 'investment', 'other')",
            name="ck_account_type",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_account_user_name"),
    )
    op.create_index(
        "ix_account_user_archived",
        "accounts",
        ["user_id", "is_archived"],
    )

    if dialect_name == "mysql":
        op.add_column(
            "transactions",
            sa.Column("account_id", sa.Integer(), nullable=True),
        )
        op.create_foreign_key(
            "fk_transactions_account_id_accounts",
            "transactions",
            "accounts",
            ["account_id"],
            ["id"],
        )
    else:
        with op.batch_alter_table("transactions", recreate="always") as batch:
            batch.add_column(sa.Column("account_id", sa.Integer(), nullable=True))
            batch.create_foreign_key(
                "fk_transactions_account_id_accounts",
                "accounts",
                ["account_id"],
                ["id"],
            )
    op.create_index("ix_tx_user_account", "transactions", ["user_id", "account_id"])

    op.create_table(
        "transfers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("from_account_id", sa.Integer(), nullable=False),
        sa.Column("to_account_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("occurred_on", sa.Date(), nullable=False),
        sa.Column("note", sa.String(length=200), nullable=True),
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
        sa.CheckConstraint("amount > 0", name="ck_transfer_amount_positive"),
        sa.CheckConstraint(
            "from_account_id <> to_account_id",
            name="ck_transfer_distinct_accounts",
        ),
        sa.ForeignKeyConstraint(["from_account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["to_account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_transfer_user_occurred",
        "transfers",
        ["user_id", "occurred_on"],
    )

    op.create_table(
        "recurring_transactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=10), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=True),
        sa.Column("frequency", sa.String(length=10), nullable=False),
        sa.Column("interval", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("next_run_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("payment_method", sa.String(length=20), nullable=True),
        sa.Column("note", sa.String(length=200), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default="1",
            nullable=False,
        ),
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
        sa.CheckConstraint(
            "frequency IN ('daily', 'weekly', 'monthly', 'yearly')",
            name="ck_recurring_frequency",
        ),
        sa.CheckConstraint(
            sa.column(sa.quoted_name("interval", True)) >= 1,
            name="ck_recurring_interval",
        ),
        sa.CheckConstraint("amount > 0", name="ck_recurring_amount_positive"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_recurring_user_active_next",
        "recurring_transactions",
        ["user_id", "is_active", "next_run_date"],
    )

    if dialect_name == "mysql":
        op.add_column(
            "budgets",
            sa.Column("category_id", sa.Integer(), nullable=True),
        )
        op.create_index("ix_budget_user", "budgets", ["user_id"])
        op.drop_constraint("uq_budget_user_month", "budgets", type_="unique")
        op.create_foreign_key(
            "fk_budgets_category_id_categories",
            "budgets",
            "categories",
            ["category_id"],
            ["id"],
        )
    else:
        with op.batch_alter_table("budgets", recreate="always") as batch:
            batch.add_column(sa.Column("category_id", sa.Integer(), nullable=True))
            batch.drop_constraint("uq_budget_user_month", type_="unique")
            batch.create_foreign_key(
                "fk_budgets_category_id_categories",
                "categories",
                ["category_id"],
                ["id"],
            )
        op.create_index("ix_budget_user", "budgets", ["user_id"])
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


def downgrade() -> None:
    """Remove account-related data and restore the original budget constraint."""
    dialect_name = op.get_bind().dialect.name
    op.drop_index("uq_budget_user_month_category", table_name="budgets")
    op.drop_index("uq_budget_user_month_total", table_name="budgets")
    if dialect_name == "mysql":
        op.drop_constraint(
            "fk_budgets_category_id_categories",
            "budgets",
            type_="foreignkey",
        )
        op.drop_column("budgets", "category_id")
        op.create_unique_constraint(
            "uq_budget_user_month",
            "budgets",
            ["user_id", "month"],
        )
    else:
        with op.batch_alter_table("budgets", recreate="always") as batch:
            batch.drop_constraint(
                "fk_budgets_category_id_categories",
                type_="foreignkey",
            )
            batch.drop_column("category_id")
            batch.create_unique_constraint(
                "uq_budget_user_month",
                ["user_id", "month"],
            )

    op.drop_index(
        "ix_recurring_user_active_next",
        table_name="recurring_transactions",
    )
    op.drop_table("recurring_transactions")
    op.drop_index("ix_transfer_user_occurred", table_name="transfers")
    op.drop_table("transfers")
    op.drop_index("ix_tx_user_account", table_name="transactions")
    if dialect_name == "mysql":
        op.drop_constraint(
            "fk_transactions_account_id_accounts",
            "transactions",
            type_="foreignkey",
        )
        op.drop_column("transactions", "account_id")
    else:
        with op.batch_alter_table("transactions", recreate="always") as batch:
            batch.drop_constraint(
                "fk_transactions_account_id_accounts",
                type_="foreignkey",
            )
            batch.drop_column("account_id")
    op.drop_index("ix_account_user_archived", table_name="accounts")
    op.drop_table("accounts")
