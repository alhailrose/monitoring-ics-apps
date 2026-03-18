from backend.interfaces.cli.main import main


def test_new_cli_entrypoint_imports_main():
    assert callable(main)
