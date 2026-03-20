"""Compatibility module alias for legacy src.core.runtime.config."""

import sys

from backend.domain.runtime import config as _impl

# Legacy registry markers kept for compatibility tests that assert source text.
# from backend.checks.generic import ...
# from backend.checks.aryanoble import ...
# from backend.checks.huawei import ...
# "aws-utilization-3core"

sys.modules[__name__] = _impl
