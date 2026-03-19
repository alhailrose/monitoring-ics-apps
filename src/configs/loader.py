"""Compatibility module alias for legacy src.configs.loader."""

import sys

from backend.config import loader as _impl

sys.modules[__name__] = _impl
