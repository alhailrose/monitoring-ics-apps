"""CLI adapter for future src-first migration."""


def main():
    from monitoring_hub.cli import main as legacy_main

    return legacy_main()


def run_cli():
    return main()


__all__ = ["main", "run_cli"]
