"""Add auth_method and credential fields to accounts

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-03-24

"""
from alembic import op
import sqlalchemy as sa

revision = 'f5a6b7c8d9e0'
down_revision = 'e4f5a6b7c8d9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('accounts', sa.Column('auth_method', sa.String(16), nullable=False, server_default='profile'))
    op.add_column('accounts', sa.Column('aws_access_key_id', sa.String(256), nullable=True))
    op.add_column('accounts', sa.Column('aws_secret_access_key_enc', sa.Text, nullable=True))
    op.add_column('accounts', sa.Column('role_arn', sa.String(512), nullable=True))
    op.add_column('accounts', sa.Column('external_id', sa.String(256), nullable=True))


def downgrade() -> None:
    op.drop_column('accounts', 'external_id')
    op.drop_column('accounts', 'role_arn')
    op.drop_column('accounts', 'aws_secret_access_key_enc')
    op.drop_column('accounts', 'aws_access_key_id')
    op.drop_column('accounts', 'auth_method')
