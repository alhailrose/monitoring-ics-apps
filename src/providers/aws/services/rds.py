"""Compatibility module alias for legacy src.providers.aws.services.rds."""

import sys

from backend.infra.cloud.aws.services import rds as _impl

sys.modules[__name__] = _impl
