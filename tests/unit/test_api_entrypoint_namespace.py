from backend.interfaces.api.main import app, create_app


def test_new_api_entrypoint_exports_app():
    assert app is not None
    assert callable(create_app)
