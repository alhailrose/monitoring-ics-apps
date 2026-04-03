"""AWS profile detection endpoints."""

from configparser import ConfigParser
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends

from backend.domain.services.auth_service import TokenPayload
from backend.infra.cloud.aws.clients import user_aws_config_path
from backend.interfaces.api.dependencies import get_customer_service, require_auth

router = APIRouter(prefix="/profiles", tags=["profiles"])

AWS_CONFIG_PATH = Path.home() / ".aws" / "config"


def _resolve_config_path_for_user(current_user: TokenPayload) -> Path:
    user_path = Path(user_aws_config_path(current_user.username))
    if user_path.exists():
        return user_path
    return AWS_CONFIG_PATH


@router.get("/detect")
def detect_profiles(service=Depends(get_customer_service)):
    """Scan ~/.aws/config and return mapped vs unmapped profiles."""
    return service.detect_profiles()


@router.get("/sso-sessions")
def list_sso_sessions(current_user: Annotated[TokenPayload, Depends(require_auth)]):
    """Return all [sso-session ...] names from ~/.aws/config."""
    sessions: list[str] = []
    config_path = _resolve_config_path_for_user(current_user)
    if config_path.exists():
        parser = ConfigParser()
        parser.read(str(config_path))
        for section in parser.sections():
            if section.startswith("sso-session "):
                sessions.append(section.removeprefix("sso-session ").strip())
    return {"sso_sessions": sorted(sessions)}


@router.get("/login-session-profiles")
def list_login_session_profiles(
    current_user: Annotated[TokenPayload, Depends(require_auth)],
):
    """Return profile names that use login_session (IAM Identity Center) auth."""
    profiles: list[str] = []
    config_path = _resolve_config_path_for_user(current_user)
    if config_path.exists():
        parser = ConfigParser()
        parser.read(str(config_path))
        for section in parser.sections():
            if parser.has_option(section, "login_session"):
                name = section.removeprefix("profile ").strip()
                profiles.append(name)
    return {"login_session_profiles": sorted(profiles)}
