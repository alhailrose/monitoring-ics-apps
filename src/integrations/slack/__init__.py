"""Compatibility package for legacy src.integrations.slack imports."""

from .app import SlackCommandService
from .commands import dispatch_slack_command, parse_slack_command
from .notifier import send_report_to_slack, send_to_webhook

__all__ = [
    "SlackCommandService",
    "dispatch_slack_command",
    "parse_slack_command",
    "send_report_to_slack",
    "send_to_webhook",
]
