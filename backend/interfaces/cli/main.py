"""CLI entrypoint in backend namespace."""

from src.app.cli.main import main


def run_cli():
    return main()


__all__ = ["main", "run_cli"]
