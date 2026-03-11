"""add_region_alarm_names_sso_session

Revision ID: 8444b20562ce
Revises: 18f6d0868678
Create Date: 2026-03-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8444b20562ce'
down_revision: Union[str, Sequence[str], None] = '18f6d0868678'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add region and alarm_names to accounts, sso_session to customers."""
    op.add_column('customers', sa.Column('sso_session', sa.String(length=128), nullable=True))
    op.add_column('accounts', sa.Column('region', sa.Text(), nullable=True))
    op.add_column('accounts', sa.Column('alarm_names', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove added columns."""
    op.drop_column('accounts', 'alarm_names')
    op.drop_column('accounts', 'region')
    op.drop_column('customers', 'sso_session')
