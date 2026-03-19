"""Compatibility module alias for legacy src.integrations.slack.notifier."""

import sys

from backend.infra.notifications.slack import notifier as _impl

sys.modules[__name__] = _impl
