"""Compatibility module alias for legacy src.core.runtime.customer_runner."""

import sys

from backend.domain.runtime import customer_runner as _impl

sys.modules[__name__] = _impl
