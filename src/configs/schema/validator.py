"""Compatibility module alias for legacy src.configs.schema.validator."""

import sys

from backend.config.schema import validator as _impl

sys.modules[__name__] = _impl
