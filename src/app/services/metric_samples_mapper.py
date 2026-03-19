"""Compatibility module alias for metric samples mapper service."""

import sys

from backend.domain.services import metric_samples_mapper as _impl

sys.modules[__name__] = _impl
