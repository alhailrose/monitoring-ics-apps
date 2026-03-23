"""expand metric_samples check_name constraint to include arbel variants and aws-utilization

Revision ID: a1b2c3d4e5f6
Revises: d5e6f7a8b9c0
Create Date: 2026-03-23

"""
from alembic import op

revision = 'a1b2c3d4e5f6'
down_revision = 'd5e6f7a8b9c0'
branch_labels = None
depends_on = None

OLD_VALUES = "'daily-arbel'"
NEW_VALUES = "'daily-arbel','daily-arbel-rds','daily-arbel-ec2','aws-utilization-3core'"


def upgrade() -> None:
    op.drop_constraint(
        'ck_metric_samples_check_name_valid',
        'metric_samples',
        type_='check',
    )
    op.create_check_constraint(
        'ck_metric_samples_check_name_valid',
        'metric_samples',
        f'check_name in ({NEW_VALUES})',
    )


def downgrade() -> None:
    op.drop_constraint(
        'ck_metric_samples_check_name_valid',
        'metric_samples',
        type_='check',
    )
    op.create_check_constraint(
        'ck_metric_samples_check_name_valid',
        'metric_samples',
        f'check_name in ({OLD_VALUES})',
    )
