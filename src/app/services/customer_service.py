"""Compatibility module alias for legacy src customer service."""

import sys

from backend.domain.services import customer_service as _impl

sys.modules[__name__] = _impl
