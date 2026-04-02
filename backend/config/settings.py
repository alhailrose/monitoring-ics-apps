"""Runtime settings for the monitoring web platform."""

from dataclasses import dataclass, field
from functools import lru_cache
import os


def _parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Invalid boolean value: {value}")


def _parse_cors_origins(raw: str | None) -> list[str]:
    if raw is None:
        return ["*"]
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    return origins or ["*"]


def _parse_csv(raw: str | None) -> list[str]:
    if raw is None:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    database_url: str
    default_region: str
    max_workers: int
    execution_timeout: int
    log_level: str
    cors_origins: list[str] = field(default_factory=lambda: ["*"])
    cors_allow_credentials: bool = False
    api_auth_enabled: bool = False
    api_keys: list[str] = field(default_factory=list)
    api_key_header: str = "X-API-Key"
    jwt_secret: str = "change-me-in-production"
    jwt_expire_hours: int = 8
    google_client_id: str = ""
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    app_base_url: str = "http://localhost:3000"
    invite_expire_hours: int = 72
    alert_forwarder_url: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    cors_origins = _parse_cors_origins(os.getenv("CORS_ORIGINS"))
    cors_allow_credentials = _parse_bool(
        os.getenv("CORS_ALLOW_CREDENTIALS"),
        default=True,
    )
    if "*" in cors_origins:
        cors_allow_credentials = False

    api_auth_enabled = _parse_bool(
        os.getenv("API_AUTH_ENABLED"),
        default=False,
    )
    api_keys = _parse_csv(os.getenv("API_KEYS"))
    if api_auth_enabled and not api_keys:
        raise ValueError("API_AUTH_ENABLED requires API_KEYS to be set")

    return Settings(
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://monitor:monitor@localhost:5432/monitoring",
        ),
        default_region=os.getenv("DEFAULT_REGION", "ap-southeast-3"),
        max_workers=int(os.getenv("MAX_WORKERS", "20")),
        execution_timeout=int(os.getenv("EXECUTION_TIMEOUT", "300")),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        cors_origins=cors_origins,
        cors_allow_credentials=cors_allow_credentials,
        api_auth_enabled=api_auth_enabled,
        api_keys=api_keys,
        api_key_header=os.getenv("API_KEY_HEADER", "X-API-Key"),
        jwt_secret=os.getenv("JWT_SECRET", "change-me-in-production"),
        jwt_expire_hours=int(os.getenv("JWT_EXPIRE_HOURS", "8")),
        google_client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
        smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_user=os.getenv("SMTP_USER", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        smtp_from=os.getenv("SMTP_FROM", ""),
        app_base_url=os.getenv("APP_BASE_URL", "http://localhost:3000"),
        invite_expire_hours=int(os.getenv("INVITE_EXPIRE_HOURS", "72")),
        alert_forwarder_url=os.getenv("ALERT_FORWARDER_URL", ""),
    )
