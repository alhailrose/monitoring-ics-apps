"""add mailing_contacts, make ticket_no nullable, add extra_data to tickets, seed Token customer

Revision ID: 3c4d5e6f7a8b
Revises: 2b3c4d5e6f7a
Create Date: 2026-04-06 00:00:00.000000

"""

from typing import Sequence, Union
from uuid import uuid4
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision: str = "3c4d5e6f7a8b"
down_revision: Union[str, None] = "2b3c4d5e6f7a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Make ticket_no nullable
    op.alter_column("tickets", "ticket_no", nullable=True)

    # 2. Add extra_data JSON column to tickets
    op.add_column("tickets", sa.Column("extra_data", sa.JSON(), nullable=True))

    # 3. Create mailing_contacts table
    op.create_table(
        "mailing_contacts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("customer_id", sa.String(36), sa.ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("email", sa.String(256), nullable=False),
        sa.Column("name", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_mailing_contacts_customer_id", "mailing_contacts", ["customer_id"])

    # 4. Seed Token customer (only if not already present)
    conn = op.get_bind()
    existing = conn.execute(
        sa.text("SELECT id FROM customers WHERE name = 'token'")
    ).fetchone()
    if not existing:
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            sa.text(
                "INSERT INTO customers (id, name, display_name, checks, slack_enabled, report_mode, created_at, updated_at) "
                "VALUES (:id, :name, :display_name, :checks, :slack_enabled, :report_mode, :created_at, :updated_at)"
            ),
            {
                "id": str(uuid4()),
                "name": "token",
                "display_name": "Token",
                "checks": "[]",
                "slack_enabled": False,
                "report_mode": "summary",
                "created_at": now,
                "updated_at": now,
            },
        )


def downgrade() -> None:
    op.drop_index("ix_mailing_contacts_customer_id", table_name="mailing_contacts")
    op.drop_table("mailing_contacts")
    op.drop_column("tickets", "extra_data")
    op.alter_column("tickets", "ticket_no", nullable=False)
