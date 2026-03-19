"""Compatibility module alias for legacy src TUI customer flow."""

import sys

from backend.interfaces.cli.flows import customer as _impl

sys.modules[__name__] = _impl
