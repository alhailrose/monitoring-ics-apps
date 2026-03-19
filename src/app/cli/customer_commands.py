"""Compatibility module alias for legacy src customer CLI commands."""

import sys

from backend.interfaces.cli import customer_commands as _impl

sys.modules[__name__] = _impl
