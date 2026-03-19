"""Compatibility module alias for legacy src.core.engine.executor."""

import sys

from backend.domain.engine import executor as _impl

sys.modules[__name__] = _impl
