"""Add status, last_seen_at, resolved_at to finding_events for deduplication

Revision ID: e4f5a6b7c8d9
Revises: c3d4e5f6a7b8
Create Date: 2026-03-24

"""
from alembic import op
import sqlalchemy as sa

revision = 'e4f5a6b7c8d9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'finding_events',
        sa.Column('status', sa.String(16), nullable=False, server_default='active'),
    )
    op.add_column(
        'finding_events',
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        'finding_events',
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    )
    # Backfill last_seen_at = created_at for all existing rows
    op.execute("UPDATE finding_events SET last_seen_at = created_at WHERE last_seen_at IS NULL")

    # Index for efficient active-finding lookups
    op.create_index(
        'idx_finding_events_account_check_key',
        'finding_events',
        ['account_id', 'check_name', 'finding_key', 'status'],
    )


def downgrade() -> None:
    op.drop_index('idx_finding_events_account_check_key', table_name='finding_events')
    op.drop_column('finding_events', 'resolved_at')
    op.drop_column('finding_events', 'last_seen_at')
    op.drop_column('finding_events', 'status')
