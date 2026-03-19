"""Compatibility module alias for legacy src API dependencies."""

import sys

from backend.interfaces.api import dependencies as _impl

sys.modules[__name__] = _impl
