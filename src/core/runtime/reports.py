"""Compatibility module alias for legacy src.core.runtime.reports."""

import sys

from backend.domain.runtime import reports as _impl

sys.modules[__name__] = _impl
