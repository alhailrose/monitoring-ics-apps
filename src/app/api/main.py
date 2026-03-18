"""Compatibility wrapper for legacy src API entrypoint."""

from backend.interfaces.api.main import app, create_app

__all__ = ["app", "create_app"]
