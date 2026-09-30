"""Add login_attempts for password login throttling.

Revision ID: 20260926_0004
Revises: 20260926_0003
Create Date: 2026-09-30
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260926_0004"
down_revision: str | Sequence[str] | None = "20260926_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def upgrade() -> None:
    """Create login_attempts: one row per email tracking failed passwords."""
    if not _has_table("login_attempts"):
        op.create_table(
            "login_attempts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("email", sa.String(length=254), nullable=False),
            sa.Column(
                "failed_count",
                sa.Integer(),
                server_default="0",
                nullable=False,
            ),
            sa.Column(
                "window_started_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "last_failed_at",
                sa.DateTime(),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("locked_until", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            # 邮箱唯一约束同时承担按邮箱查询的索引职责，无需再建普通索引。
            sa.UniqueConstraint("email", name="uq_login_attempts_email"),
        )


def downgrade() -> None:
    """Drop login_attempts."""
    if _has_table("login_attempts"):
        op.drop_table("login_attempts")
