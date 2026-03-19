"""Compatibility module alias for legacy src TUI cloudwatch/cost flow."""

import sys

from backend.interfaces.cli.flows import cloudwatch_cost as _impl

sys.modules[__name__] = _impl
