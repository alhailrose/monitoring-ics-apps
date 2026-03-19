"""Compatibility module alias for legacy src TUI settings flow."""

import sys

from backend.interfaces.cli.flows import settings as _impl

sys.modules[__name__] = _impl
