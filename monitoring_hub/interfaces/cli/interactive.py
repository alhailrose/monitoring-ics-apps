"""Interactive terminal mode compatibility entrypoint."""

from src.app.tui.interactive import run_interactive


def main():
    return run_interactive()


__all__ = ["main", "run_interactive"]
