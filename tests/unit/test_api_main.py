from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from backend.config.settings import get_settings


def setup_function():
    get_settings.cache_clear()


def teardown_function():
    get_settings.cache_clear()


def test_liveness_endpoint_returns_ok():
    from backend.interfaces.api.main import create_app

    app = create_app()
    client = TestClient(app)

    response = client.get("/health/liveness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"


def test_readiness_endpoint_returns_db_check(monkeypatch):
    import backend.interfaces.api.dependencies as deps
    from backend.interfaces.api.main import create_app

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    factory = sessionmaker(
        bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
    )
    monkeypatch.setattr(deps, "_get_session_factory", lambda: factory)

    app = create_app()
    client = TestClient(app)

    response = client.get("/health/readiness")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["checks"]["database"] == "ok"


def test_api_auth_enforced_when_enabled(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEYS", "top-secret")
    monkeypatch.setenv("JWT_SECRET", "test-secret-not-default-value-32x")

    from backend.interfaces.api.main import create_app

    app = create_app()
    client = TestClient(app)

    response = client.get("/api/v1/checks/available")

    assert response.status_code == 401


def test_api_auth_accepts_x_api_key_header(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEYS", "top-secret")
    monkeypatch.setenv("JWT_SECRET", "test-secret-not-default-value-32x")

    from backend.interfaces.api.main import create_app

    app = create_app()
    client = TestClient(app)

    response = client.get(
        "/api/v1/checks/available",
        headers={"X-API-Key": "top-secret"},
    )

    assert response.status_code == 200


def test_api_auth_accepts_bearer_token(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEYS", "top-secret")
    monkeypatch.setenv("JWT_SECRET", "test-secret-not-default-value-32x")

    from backend.interfaces.api.main import create_app

    app = create_app()
    client = TestClient(app)

    response = client.get(
        "/api/v1/checks/available",
        headers={"Authorization": "Bearer top-secret"},
    )

    assert response.status_code == 200
