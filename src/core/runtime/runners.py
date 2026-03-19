"""Compatibility module alias for legacy src.core.runtime.runners."""

import sys

from backend.domain.runtime import runners as _impl

sys.modules[__name__] = _impl
