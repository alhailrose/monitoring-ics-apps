"""Compatibility module alias for legacy src.core.models.jobs."""

import sys

import backend.domain.models as _impl

sys.modules[__name__] = _impl
