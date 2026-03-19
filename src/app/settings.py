"""Compatibility module alias for legacy src settings."""

import sys

from backend.config import settings as _impl

sys.modules[__name__] = _impl
