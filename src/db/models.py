"""Compatibility module alias for legacy src.db.models."""

import sys

from backend.infra.database import models as _impl

sys.modules[__name__] = _impl
