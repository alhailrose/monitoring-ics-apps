"""Compatibility module alias for legacy src session health service."""

import sys

from backend.domain.services import session_health as _impl

sys.modules[__name__] = _impl
