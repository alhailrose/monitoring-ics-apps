"""add metric_samples table

Revision ID: f3d2a4b8c91e
Revises: 9b4de82e1b11
Create Date: 2026-03-19 18:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3d2a4b8c91e"
down_revision: Union[str, Sequence[str], None] = "9b4de82e1b11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "metric_samples",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("check_run_id", sa.String(length=36), nullable=False),
        sa.Column("account_id", sa.String(length=36), nullable=False),
        sa.Column("check_name", sa.String(length=128), nullable=False),
        sa.Column("metric_name", sa.String(length=128), nullable=False),
        sa.Column("metric_status", sa.String(length=32), nullable=False),
        sa.Column("value_num", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("resource_role", sa.String(length=128), nullable=True),
        sa.Column("resource_id", sa.String(length=256), nullable=True),
        sa.Column("resource_name", sa.String(length=256), nullable=True),
        sa.Column("service_type", sa.String(length=32), nullable=True),
        sa.Column("section_name", sa.String(length=256), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "check_name in ('daily-arbel')",
            name="ck_metric_samples_check_name_valid",
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["check_run_id"], ["check_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_metric_samples_account_metric",
        "metric_samples",
        ["account_id", "metric_name", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_metric_samples_account_id"),
        "metric_samples",
        ["account_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_metric_samples_check_name"),
        "metric_samples",
        ["check_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_metric_samples_check_run_id"),
        "metric_samples",
        ["check_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_metric_samples_metric_name"),
        "metric_samples",
        ["metric_name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_metric_samples_metric_name"), table_name="metric_samples")
    op.drop_index(op.f("ix_metric_samples_check_run_id"), table_name="metric_samples")
    op.drop_index(op.f("ix_metric_samples_check_name"), table_name="metric_samples")
    op.drop_index(op.f("ix_metric_samples_account_id"), table_name="metric_samples")
    op.drop_index("idx_metric_samples_account_metric", table_name="metric_samples")
    op.drop_table("metric_samples")
