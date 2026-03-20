"""Compatibility module alias for legacy src.checks path."""

import sys

import backend.checks.huawei.ecs_utilization as _impl

sys.modules[__name__] = _impl
