"""TUI adapter module."""


def run_interactive():
    from monitoring_hub.interactive import run_interactive as legacy_run_interactive

    return legacy_run_interactive()


def run_interactive_v2():
    try:  # Optional until v2 module exists in this branch baseline
        from monitoring_hub.interactive_v2 import run_interactive_v2 as legacy_v2  # type: ignore

        return legacy_v2()
    except Exception:  # pragma: no cover
        return run_interactive()


__all__ = ["run_interactive", "run_interactive_v2"]
