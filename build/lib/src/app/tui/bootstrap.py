"""Canonical TUI bootstrap exports."""


def run_interactive():
    from src.app.tui import interactive

    return interactive.run_interactive()


def run_interactive_v2():
    from src.app.tui import interactive

    return interactive.run_interactive_v2()


__all__ = ["run_interactive", "run_interactive_v2"]
