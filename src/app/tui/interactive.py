"""Compatibility module alias for legacy src TUI interactive."""

import sys

from backend.interfaces.cli import interactive as _impl

sys.modules[__name__] = _impl
