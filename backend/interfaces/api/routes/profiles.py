"""AWS profile detection endpoints."""

from configparser import ConfigParser
from pathlib import Path

from fastapi import APIRouter, Depends

from backend.interfaces.api.dependencies import get_customer_service

router = APIRouter(prefix="/profiles", tags=["profiles"])

AWS_CONFIG_PATH = Path.home() / ".aws" / "config"


@router.get("/detect")
def detect_profiles(service=Depends(get_customer_service)):
    """Scan ~/.aws/config and return mapped vs unmapped profiles."""
    return service.detect_profiles()


@router.get("/sso-sessions")
def list_sso_sessions():
    """Return all [sso-session ...] names from ~/.aws/config."""
    sessions: list[str] = []
    if AWS_CONFIG_PATH.exists():
        parser = ConfigParser()
        parser.read(str(AWS_CONFIG_PATH))
        for section in parser.sections():
            if section.startswith("sso-session "):
                sessions.append(section.removeprefix("sso-session ").strip())
    return {"sso_sessions": sorted(sessions)}
