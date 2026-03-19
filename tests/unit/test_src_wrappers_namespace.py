from src.app.api.main import app, create_app
from src.app.cli.main import main


def test_src_api_wrapper_points_to_backend_namespace():
    assert app is not None
    assert callable(create_app)


def test_src_cli_wrapper_points_to_backend_namespace():
    assert callable(main)
