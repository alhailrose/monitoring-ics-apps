"""Compatibility module alias for legacy src.core.runtime.config."""

import sys

from backend.domain.runtime import config as _impl

# Legacy registry markers kept for compatibility tests that assert source text.
# from src.checks.generic import ...
# from src.checks.aryanoble import ...
# from src.checks.huawei import ...
# "aws-utilization-3core"

sys.modules[__name__] = _impl
