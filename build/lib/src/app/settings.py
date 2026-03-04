"""Runtime settings for the monitoring web platform."""

from dataclasses import dataclass, field
from functools import lru_cache
import os


@dataclass(frozen=True)
class Settings:
    database_url: str
    default_region: str
    max_workers: int
    execution_timeout: int
    cors_origins: list[str] = field(default_factory=lambda: ["*"])


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://monitor:monitor@localhost:5432/monitoring",
        ),
        default_region=os.getenv("DEFAULT_REGION", "ap-southeast-3"),
        max_workers=int(os.getenv("MAX_WORKERS", "5")),
        execution_timeout=int(os.getenv("EXECUTION_TIMEOUT", "300")),
        cors_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    )
