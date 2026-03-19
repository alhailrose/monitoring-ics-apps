"""Compatibility module alias for legacy src TUI dashboard flow."""

import sys

from backend.interfaces.cli.flows import dashboard as _impl

sys.modules[__name__] = _impl
