"""add customer target to tickets

Revision ID: 2b3c4d5e6f7a
Revises: 1a2b3c4d5e6f
Create Date: 2026-04-03 19:20:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "2b3c4d5e6f7a"
down_revision: Union[str, None] = "1a2b3c4d5e6f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("customer_id", sa.String(36), nullable=True))
    op.create_index("ix_tickets_customer_id", "tickets", ["customer_id"], unique=False)
    op.create_foreign_key(
        "fk_tickets_customer_id_customers",
        "tickets",
        "customers",
        ["customer_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_tickets_customer_id_customers", "tickets", type_="foreignkey"
    )
    op.drop_index("ix_tickets_customer_id", table_name="tickets")
    op.drop_column("tickets", "customer_id")
