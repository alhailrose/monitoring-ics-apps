import pytest

from backend.config.settings import get_settings


def setup_function():
    get_settings.cache_clear()


def teardown_function():
    get_settings.cache_clear()


def test_runtime_settings_load_defaults(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DEFAULT_REGION", raising=False)
    monkeypatch.delenv("MAX_WORKERS", raising=False)
    monkeypatch.delenv("EXECUTION_TIMEOUT", raising=False)
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    settings = get_settings()

    assert (
        settings.database_url
        == "postgresql+psycopg://monitor:monitor@localhost:5432/monitoring"
    )
    assert settings.default_region == "ap-southeast-3"
    assert settings.max_workers == 5
    assert settings.execution_timeout == 300
    assert settings.cors_origins == ["*"]
    assert settings.cors_allow_credentials is False


def test_runtime_settings_env_override(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@db:5432/app")
    monkeypatch.setenv("DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("MAX_WORKERS", "12")
    monkeypatch.setenv("EXECUTION_TIMEOUT", "900")
    monkeypatch.setenv(
        "CORS_ORIGINS", "https://ops.example.com,https://admin.example.com"
    )

    settings = get_settings()

    assert settings.database_url == "postgresql+psycopg://u:p@db:5432/app"
    assert settings.default_region == "us-east-1"
    assert settings.max_workers == 12
    assert settings.execution_timeout == 900
    assert settings.cors_origins == [
        "https://ops.example.com",
        "https://admin.example.com",
    ]
    assert settings.cors_allow_credentials is True


def test_runtime_settings_disables_credentials_for_wildcard_cors(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "*")
    monkeypatch.setenv("CORS_ALLOW_CREDENTIALS", "true")

    settings = get_settings()

    assert settings.cors_origins == ["*"]
    assert settings.cors_allow_credentials is False


def test_runtime_settings_enables_credentials_for_specific_origins(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://ops.example.com")
    monkeypatch.setenv("CORS_ALLOW_CREDENTIALS", "true")

    settings = get_settings()

    assert settings.cors_origins == ["https://ops.example.com"]
    assert settings.cors_allow_credentials is True


def test_runtime_settings_rejects_invalid_numeric(monkeypatch):
    monkeypatch.setenv("MAX_WORKERS", "not-a-number")

    with pytest.raises(ValueError):
        get_settings()


def test_runtime_settings_enables_api_auth_from_env(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEYS", "token-a, token-b")
    monkeypatch.setenv("API_KEY_HEADER", "X-Internal-Key")

    settings = get_settings()

    assert settings.api_auth_enabled is True
    assert settings.api_keys == ["token-a", "token-b"]
    assert settings.api_key_header == "X-Internal-Key"


def test_runtime_settings_rejects_enabled_auth_without_keys(monkeypatch):
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    monkeypatch.delenv("API_KEYS", raising=False)

    with pytest.raises(ValueError):
        get_settings()
