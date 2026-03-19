"""Compatibility module alias for legacy src.db.repositories.customer_repository."""

import sys

from backend.infra.database.repositories import customer_repository as _impl

sys.modules[__name__] = _impl
