"""add ticketing table

Revision ID: 1a2b3c4d5e6f
Revises: fa3b91c2d847
Create Date: 2026-04-03 14:40:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "1a2b3c4d5e6f"
down_revision: Union[str, None] = "fa3b91c2d847"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tickets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ticket_no", sa.String(32), nullable=False, unique=True),
        sa.Column("task", sa.String(512), nullable=False),
        sa.Column("pic", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("description_solution", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status in ('open','in_progress','resolved','closed')",
            name="ck_tickets_status_valid",
        ),
    )
    op.create_index("ix_tickets_ticket_no", "tickets", ["ticket_no"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_tickets_ticket_no", table_name="tickets")
    op.drop_table("tickets")
