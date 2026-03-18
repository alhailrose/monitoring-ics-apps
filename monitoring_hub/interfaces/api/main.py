"""API entrypoint in monitoring_hub namespace."""

from src.app.api.main import app, create_app

__all__ = ["app", "create_app"]
