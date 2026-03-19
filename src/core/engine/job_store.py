"""Compatibility module alias for legacy src.core.engine.job_store."""

import sys

from backend.domain.engine import job_store as _impl

sys.modules[__name__] = _impl
