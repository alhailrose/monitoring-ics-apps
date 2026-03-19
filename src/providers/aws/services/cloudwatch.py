"""Compatibility module alias for legacy src.providers.aws.services.cloudwatch."""

import sys

from backend.infra.cloud.aws.services import cloudwatch as _impl

sys.modules[__name__] = _impl
