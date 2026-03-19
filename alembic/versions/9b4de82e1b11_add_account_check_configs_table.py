"""add account_check_configs table

Revision ID: 9b4de82e1b11
Revises: 4c3f9a7a52d1
Create Date: 2026-03-19 16:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9b4de82e1b11"
down_revision: Union[str, Sequence[str], None] = "4c3f9a7a52d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "account_check_configs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("account_id", sa.String(length=36), nullable=False),
        sa.Column("check_name", sa.String(length=128), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "check_name", name="uq_account_check_config"),
    )
    op.create_index(
        "idx_account_check_config_account",
        "account_check_configs",
        ["account_id"],
        unique=False,
    )
    op.create_index(
        "idx_account_check_config_check",
        "account_check_configs",
        ["check_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_account_check_configs_account_id"),
        "account_check_configs",
        ["account_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_account_check_configs_account_id"), table_name="account_check_configs"
    )
    op.drop_index("idx_account_check_config_check", table_name="account_check_configs")
    op.drop_index(
        "idx_account_check_config_account", table_name="account_check_configs"
    )
    op.drop_table("account_check_configs")
