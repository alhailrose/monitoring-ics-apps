"""Compatibility wrapper for Slack integration modules."""

from src.integrations.slack import app, commands, notifier

__all__ = ["app", "commands", "notifier"]
