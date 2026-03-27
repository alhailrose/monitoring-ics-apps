"""Shared metric-sample domain constants."""

from __future__ import annotations

METRIC_SAMPLE_CHECK_DAILY_ARBEL = "daily-arbel"
METRIC_SAMPLE_CHECK_AWS_UTILIZATION = "ec2_utilization"

# daily-arbel-rds / daily-arbel-ec2 use the same DailyArbelChecker output format
# but are registered under different names when run as dedicated/single checks
METRIC_SAMPLE_ARBEL_VARIANTS = frozenset(
    [
        "daily-arbel",
        "daily-arbel-rds",
        "daily-arbel-ec2",
    ]
)

METRIC_SAMPLE_CHECK_NAMES = (
    # Utilization / performance metrics
    "daily-arbel",
    "daily-arbel-rds",
    "daily-arbel-ec2",
    "ec2_utilization",
    # Security & compliance counts
    "guardduty",
    "cloudwatch",
    # Cost anomaly counts
    "cost",
    # Operational health counts
    "backup",
    "notifications",
)
METRIC_SAMPLE_CHECKS = frozenset(METRIC_SAMPLE_CHECK_NAMES)

# Checks that represent workload/utilization trends (for dashboard trend KPIs)
WORKLOAD_METRIC_SAMPLE_CHECKS = frozenset(
    {
        "ec2_utilization",
        "daily-arbel",
        "daily-arbel-rds",
        "daily-arbel-ec2",
    }
)
