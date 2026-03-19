"""Compatibility module alias for legacy src.core.runtime.ui."""

import sys

from backend.domain.runtime import ui as _impl

sys.modules[__name__] = _impl
