"""Compatibility module alias for legacy src.checks path."""

import sys

import backend.checks.common.aws_errors as _impl

sys.modules[__name__] = _impl
