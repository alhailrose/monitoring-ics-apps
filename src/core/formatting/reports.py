"""Compatibility module alias for legacy src.core.formatting.reports."""

import sys

from backend.domain.formatting import reports as _impl

sys.modules[__name__] = _impl
