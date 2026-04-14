"""add check_jobs table for async job persistence

Revision ID: 4d5e6f7a8b9c
Revises: 3c4d5e6f7a8b
Create Date: 2026-04-14 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4d5e6f7a8b9c"
down_revision: Union[str, None] = "3c4d5e6f7a8b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "check_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("customer_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("mode", sa.String(32), nullable=True),
        sa.Column("check_name", sa.String(128), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_check_jobs_status", "check_jobs", ["status"])
    op.create_index(
        "idx_check_jobs_status_created", "check_jobs", ["status", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("idx_check_jobs_status_created", table_name="check_jobs")
    op.drop_index("ix_check_jobs_status", table_name="check_jobs")
    op.drop_table("check_jobs")
