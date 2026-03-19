"""Compatibility module alias for legacy src.core.runtime.config."""

import sys

from backend.domain.runtime import config as _impl

sys.modules[__name__] = _impl
