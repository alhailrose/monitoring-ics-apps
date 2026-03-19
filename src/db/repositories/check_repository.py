"""Compatibility module alias for legacy src.db.repositories.check_repository."""

import sys

from backend.infra.database.repositories import check_repository as _impl

sys.modules[__name__] = _impl
