"""add_customer_report_mode_and_label

Revision ID: d5e6f7a8b9c0
Revises: c7f8a9b2d3e4
Create Date: 2026-03-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, None] = 'c7f8a9b2d3e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add report_mode and label columns to customers."""
    op.add_column('customers', sa.Column('report_mode', sa.String(length=32), nullable=False, server_default='summary'))
    op.add_column('customers', sa.Column('label', sa.String(length=256), nullable=True))


def downgrade() -> None:
    """Remove report_mode and label columns."""
    op.drop_column('customers', 'label')
    op.drop_column('customers', 'report_mode')
