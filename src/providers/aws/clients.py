"""Compatibility module alias for legacy src.providers.aws.clients."""

import sys

from backend.infra.cloud.aws import clients as _impl

sys.modules[__name__] = _impl
