from backend.interfaces.cli import interactive


def test_cli_interactive_module_exists():
    assert hasattr(interactive, "main")
