from src.app.api.main import create_app
from src.app.cli import main as cli_main
from src.app.tui.interactive import run_interactive
from src.core.engine.jobs import JobExecutor, JobStore
from src.core.models.jobs import JobRecord


def test_src_cli_exposes_run_cli_alias():
    assert callable(cli_main.run_cli)


def test_src_tui_exposes_interactive_entrypoint():
    assert callable(run_interactive)


def test_src_core_job_types_are_exported():
    assert JobExecutor is not None
    assert JobStore is not None
    assert JobRecord is not None


def test_src_api_placeholder_shape():
    app = create_app()
    assert app.get("status") == "not-implemented"
