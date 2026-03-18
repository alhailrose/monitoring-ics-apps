"""Compatibility wrapper for legacy src CLI entrypoint."""

from backend.interfaces.cli.main import main, run_cli

__all__ = ["main", "run_cli"]
