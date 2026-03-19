"""Compatibility module alias for legacy src.integrations.slack.app."""

import sys

from backend.infra.notifications.slack import app as _impl

sys.modules[__name__] = _impl
