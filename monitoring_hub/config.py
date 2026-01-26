"""
Configuration constants for AWS Monitoring Hub.
Uses external config loader with fallback to built-in defaults.
"""

from rich.console import Console
from questionary import Style

from checks.health_events import HealthChecker
from checks.cost_anomalies import CostAnomalyChecker
from checks.guardduty import GuardDutyChecker
from checks.cloudwatch_alarms import CloudWatchAlarmChecker
from checks.notifications import NotificationChecker
from checks.backup_status import BackupStatusChecker
from checks.rds_metrics import RDSMetricsChecker
from checks.ec2_list import EC2ListChecker

from .config_loader import (
    get_profile_groups,
    get_display_names,
    get_default_region,
    get_default_workers,
    get_config,
    create_sample_config,
    CONFIG_FILE,
)

# Re-export config loader functions
__all__ = [
    "PROFILE_GROUPS",
    "AVAILABLE_CHECKS",
    "ALL_MODE_CHECKS",
    "ALL_MODE_CHECKS_NO_BACKUP_RDS",
    "BACKUP_DISPLAY_NAMES",
    "CUSTOM_STYLE",
    "TIPS",
    "console",
    "get_last_interrupt_ts",
    "set_last_interrupt_ts",
    "INTERRUPT_EXIT_WINDOW",
    "RESET",
    "BOLD",
    "DIM",
    "CYAN",
    "GREEN",
    "YELLOW",
    "MAGENTA",
    "DEFAULT_REGION",
    "DEFAULT_WORKERS",
]


# Profile groups - loaded from external config or defaults
def _get_profile_groups():
    """Lazy load profile groups from config."""
    return get_profile_groups()


# Property-like access for backward compatibility
class _ProfileGroupsProxy:
    """Proxy class to lazily load profile groups."""

    def __getitem__(self, key):
        return get_profile_groups()[key]

    def __contains__(self, key):
        return key in get_profile_groups()

    def __iter__(self):
        return iter(get_profile_groups())

    def keys(self):
        return get_profile_groups().keys()

    def values(self):
        return get_profile_groups().values()

    def items(self):
        return get_profile_groups().items()

    def get(self, key, default=None):
        return get_profile_groups().get(key, default)


PROFILE_GROUPS = _ProfileGroupsProxy()

# Display names for WhatsApp reports
BACKUP_DISPLAY_NAMES = get_display_names()

# Default settings from config
DEFAULT_REGION = get_default_region()
DEFAULT_WORKERS = get_default_workers()

# Available checks mapping
AVAILABLE_CHECKS = {
    "health": HealthChecker,
    "cost": CostAnomalyChecker,
    "guardduty": GuardDutyChecker,
    "cloudwatch": CloudWatchAlarmChecker,
    "notifications": NotificationChecker,
    "backup": BackupStatusChecker,
    "rds": RDSMetricsChecker,
    "ec2list": EC2ListChecker,
}

# Checks to run in --all mode (excludes health only)
ALL_MODE_CHECKS = {
    "cost": CostAnomalyChecker,
    "guardduty": GuardDutyChecker,
    "cloudwatch": CloudWatchAlarmChecker,
    "notifications": NotificationChecker,
    "backup": BackupStatusChecker,
    "rds": RDSMetricsChecker,
}

# Checks to run in lightweight --all mode (no backup/rds)
ALL_MODE_CHECKS_NO_BACKUP_RDS = {
    "cost": CostAnomalyChecker,
    "guardduty": GuardDutyChecker,
    "cloudwatch": CloudWatchAlarmChecker,
    "notifications": NotificationChecker,
}

# Interrupt handling
INTERRUPT_EXIT_WINDOW = 1.5
_last_interrupt_ts = 0.0


def get_last_interrupt_ts():
    """Get last interrupt timestamp."""
    global _last_interrupt_ts
    return _last_interrupt_ts


def set_last_interrupt_ts(value):
    """Set last interrupt timestamp."""
    global _last_interrupt_ts
    _last_interrupt_ts = value


# Minimal ANSI helpers for a brighter CLI without extra deps
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"

# Rich console instance
console = Console()

# Custom style for cooler prompts
CUSTOM_STYLE = Style(
    [
        ("qmark", "fg:#00b894 bold"),
        ("question", "bold"),
        ("answer", "fg:#00cec9 bold"),
        ("pointer", "fg:#00e0a3 bold"),
        ("highlighted", "fg:#00e0a3 bold"),
        ("selected", "fg:#0a0a0a bg:#00e0a3"),
        ("separator", "fg:#636e72"),
        ("instruction", "fg:#b2bec3"),
    ]
)

# Tips for interactive mode
TIPS = [
    "Esc/Ctrl+C selalu membawa Anda ke menu utama.",
    "Gunakan Group (SSO) agar daftar akun otomatis terisi.",
    "Backup dan RDS mendukung multi akun untuk laporan WhatsApp.",
    "Single check cocok untuk verifikasi cepat per profil.",
    "Pilih region sesuai default profil untuk menghindari error.",
    f"Config eksternal: {CONFIG_FILE}",
    "Parallel execution mempercepat multi-account checks.",
]
