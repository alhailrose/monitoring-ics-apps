"""Compatibility module alias for legacy src.core.runtime.config_loader."""

import sys

from backend.domain.runtime import config_loader as _impl

sys.modules[__name__] = _impl
