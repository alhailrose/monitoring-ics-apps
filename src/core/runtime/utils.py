"""Compatibility module alias for legacy src.core.runtime.utils."""

import sys

from backend.domain.runtime import utils as _impl

sys.modules[__name__] = _impl
