"""Compatibility wrapper for TUI scaffold path."""

from backend.interfaces.cli.main import main as _main


def main() -> int:
    return _main()


if __name__ == "__main__":
    raise SystemExit(main())
