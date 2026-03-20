"""Compatibility module alias for legacy src.checks path."""

import sys

import backend.checks as _impl

sys.modules[__name__] = _impl
