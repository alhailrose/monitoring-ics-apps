"""Compatibility module alias for legacy src.db.session."""

import sys

from backend.infra.database import session as _impl

sys.modules[__name__] = _impl
