"""Compatibility module alias for legacy src TUI common helpers."""

import sys

from backend.interfaces.cli import common as _impl

sys.modules[__name__] = _impl
