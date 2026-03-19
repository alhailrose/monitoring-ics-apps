"""Compatibility module alias for legacy src.providers.aws.auth."""

import sys

from backend.infra.cloud.aws import auth as _impl

sys.modules[__name__] = _impl
