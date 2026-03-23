"""rename aws-utilization-3core to ec2_utilization

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-03-23

"""
from alembic import op

revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None

OLD = 'aws-utilization-3core'
NEW = 'ec2_utilization'


def upgrade() -> None:
    op.execute(f"UPDATE metric_samples SET check_name = '{NEW}' WHERE check_name = '{OLD}'")
    op.execute(f"UPDATE check_results SET check_name = '{NEW}' WHERE check_name = '{OLD}'")
    op.execute(f"UPDATE check_runs SET check_name = '{NEW}' WHERE check_name = '{OLD}'")


def downgrade() -> None:
    op.execute(f"UPDATE metric_samples SET check_name = '{OLD}' WHERE check_name = '{NEW}'")
    op.execute(f"UPDATE check_results SET check_name = '{OLD}' WHERE check_name = '{NEW}'")
    op.execute(f"UPDATE check_runs SET check_name = '{OLD}' WHERE check_name = '{NEW}'")
