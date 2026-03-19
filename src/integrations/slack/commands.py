"""Compatibility module alias for legacy src.integrations.slack.commands."""

import sys

from backend.infra.notifications.slack import commands as _impl

sys.modules[__name__] = _impl
