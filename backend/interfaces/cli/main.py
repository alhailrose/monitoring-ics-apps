"""CLI entrypoints in backend namespace."""

from src.app.cli.bootstrap import main


def run_cli():
    return main()


__all__ = ["main", "run_cli"]
