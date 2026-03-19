"""Compatibility module alias for finding events mapper service."""

import sys

from backend.domain.services import finding_events_mapper as _impl

sys.modules[__name__] = _impl
