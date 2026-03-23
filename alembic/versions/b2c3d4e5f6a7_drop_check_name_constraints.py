"""drop hardcoded check_name constraints from finding_events and metric_samples

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-23

"""
from alembic import op

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None

_FINDING_OLD = "'daily-arbel','daily-arbel-rds','daily-arbel-ec2','aws-utilization-3core','cost-anomaly','guardduty','cloudwatch-alarms','backup','notifications'"
_METRIC_OLD = "'daily-arbel','daily-arbel-rds','daily-arbel-ec2','aws-utilization-3core'"


def upgrade() -> None:
    op.drop_constraint(
        'ck_finding_events_check_name_valid',
        'finding_events',
        type_='check',
    )
    op.drop_constraint(
        'ck_metric_samples_check_name_valid',
        'metric_samples',
        type_='check',
    )


def downgrade() -> None:
    op.create_check_constraint(
        'ck_finding_events_check_name_valid',
        'finding_events',
        f'check_name in ({_FINDING_OLD})',
    )
    op.create_check_constraint(
        'ck_metric_samples_check_name_valid',
        'metric_samples',
        f'check_name in ({_METRIC_OLD})',
    )
