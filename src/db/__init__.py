"""Compatibility package for legacy src.db imports."""

from src.db import models, session

__all__ = ["models", "session"]
