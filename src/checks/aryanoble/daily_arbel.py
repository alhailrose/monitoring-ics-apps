"""Compatibility module alias for legacy src.checks path."""

import sys

import backend.checks.aryanoble.daily_arbel as _impl

sys.modules[__name__] = _impl
