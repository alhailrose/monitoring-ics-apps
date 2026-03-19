"""add finding_events table

Revision ID: 4c3f9a7a52d1
Revises: 8444b20562ce
Create Date: 2026-03-19 10:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4c3f9a7a52d1"
down_revision: Union[str, Sequence[str], None] = "8444b20562ce"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "finding_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("check_run_id", sa.String(length=36), nullable=False),
        sa.Column("account_id", sa.String(length=36), nullable=False),
        sa.Column("check_name", sa.String(length=128), nullable=False),
        sa.Column("finding_key", sa.String(length=256), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "check_name in ('guardduty','cloudwatch','notifications','backup')",
            name="ck_finding_events_check_name_valid",
        ),
        sa.CheckConstraint(
            "severity in ('INFO','LOW','MEDIUM','HIGH','CRITICAL','ALARM')",
            name="ck_finding_events_severity_valid",
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["check_run_id"], ["check_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_finding_events_account_check",
        "finding_events",
        ["account_id", "check_name", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_finding_events_account_id"),
        "finding_events",
        ["account_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_finding_events_check_name"),
        "finding_events",
        ["check_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_finding_events_check_run_id"),
        "finding_events",
        ["check_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_finding_events_check_run_id"), table_name="finding_events")
    op.drop_index(op.f("ix_finding_events_check_name"), table_name="finding_events")
    op.drop_index(op.f("ix_finding_events_account_id"), table_name="finding_events")
    op.drop_index("idx_finding_events_account_check", table_name="finding_events")
    op.drop_table("finding_events")
