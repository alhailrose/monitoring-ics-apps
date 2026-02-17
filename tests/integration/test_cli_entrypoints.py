import src.app.cli.bootstrap as src_cli_bootstrap
import src.app.tui.bootstrap as src_tui_bootstrap
from pathlib import Path


def test_src_cli_bootstrap_exposes_main():
    assert callable(src_cli_bootstrap.main)


def test_src_tui_bootstrap_exposes_entrypoints():
    assert callable(src_tui_bootstrap.run_interactive)
    assert callable(src_tui_bootstrap.run_interactive_v2)


def test_pyproject_script_points_to_src_runtime():
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    assert 'monitoring-hub = "src.app.cli.main:main"' in pyproject
