"""Compatibility module alias for legacy src.providers.aws.services.budgets."""

import sys

from backend.infra.cloud.aws.services import budgets as _impl

sys.modules[__name__] = _impl
