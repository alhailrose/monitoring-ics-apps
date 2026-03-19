"""Compatibility module alias for legacy src.core.engine.jobs."""

import sys

import backend.domain.engine as _impl

sys.modules[__name__] = _impl
