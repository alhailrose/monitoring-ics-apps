"""Compatibility package for legacy src.db.repositories imports."""

from .check_repository import CheckRepository
from .customer_repository import CustomerRepository

__all__ = ["CheckRepository", "CustomerRepository"]
