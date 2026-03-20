"""Compatibility module alias for legacy src.checks path."""

import sys

import backend.checks.generic.cost_anomalies as _impl

sys.modules[__name__] = _impl
