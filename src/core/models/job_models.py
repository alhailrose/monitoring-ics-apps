"""Compatibility module alias for legacy src.core.models.job_models."""

import sys

from backend.domain.models import job_models as _impl

sys.modules[__name__] = _impl
