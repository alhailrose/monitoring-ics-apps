"""Compatibility module alias for legacy src TUI arbel flow."""

import sys

from backend.interfaces.cli.flows import arbel as _impl

sys.modules[__name__] = _impl
