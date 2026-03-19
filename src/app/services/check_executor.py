"""Compatibility module alias for legacy src check executor service."""

import sys

from backend.domain.services import check_executor as _impl

sys.modules[__name__] = _impl
