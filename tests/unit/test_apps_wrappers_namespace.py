from apps.api.main import app, create_app
from apps.tui.main import main


def test_apps_api_wrapper_uses_new_namespace():
    assert app is not None
    assert callable(create_app)


def test_apps_tui_wrapper_uses_new_namespace():
    assert callable(main)
