"""Compatibility package for legacy src.db.repositories imports."""

from src.db.repositories.check_repository import CheckRepository
from src.db.repositories.customer_repository import CustomerRepository

__all__ = ["CheckRepository", "CustomerRepository"]
