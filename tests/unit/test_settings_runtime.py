import pytest

from src.app.settings import get_settings


def setup_function():
    get_settings.cache_clear()


def teardown_function():
    get_settings.cache_clear()


def test_runtime_settings_load_defaults(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("EXECUTION_MODE", raising=False)

    settings = get_settings()

    assert settings.database_url == "postgresql+psycopg://monitor:monitor@postgres:5432/monitoring"
    assert settings.redis_url == "redis://redis:6379/0"
    assert settings.execution_mode == "local"


def test_runtime_settings_env_override(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@db:5432/app")
    monkeypatch.setenv("REDIS_URL", "redis://cache:6379/1")
    monkeypatch.setenv("EXECUTION_MODE", "api")

    settings = get_settings()

    assert settings.database_url == "postgresql+psycopg://u:p@db:5432/app"
    assert settings.redis_url == "redis://cache:6379/1"
    assert settings.execution_mode == "api"


def test_runtime_settings_rejects_invalid_mode(monkeypatch):
    monkeypatch.setenv("EXECUTION_MODE", "worker")

    with pytest.raises(ValueError, match="Invalid EXECUTION_MODE"):
        get_settings()
