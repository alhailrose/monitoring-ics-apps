"""AWS config template and per-user config management endpoints."""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.interfaces.api.dependencies import require_auth, require_role
from backend.domain.services.auth_service import TokenPayload

router = APIRouter(prefix="/settings", tags=["settings"])

_TEMPLATE_PATH = os.path.expanduser("~/.aws/aws-config.template")
_SYSTEM_CONFIG = os.path.expanduser("~/.aws/config")


def _read_default_template() -> str:
    """Return the system ~/.aws/config as the seed, or an empty string."""
    if os.path.exists(_SYSTEM_CONFIG):
        with open(_SYSTEM_CONFIG) as f:
            return f.read()
    return ""


def _user_config_path(username: str) -> str:
    return os.path.expanduser(f"~/.aws/users/{username}/config")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class TemplateResponse(BaseModel):
    content: str
    is_default: bool


class TemplateUpdate(BaseModel):
    content: str


class UserConfigResponse(BaseModel):
    content: str
    username: str


# ---------------------------------------------------------------------------
# Template management (super_user only for write)
# ---------------------------------------------------------------------------


@router.get("/aws-template", response_model=TemplateResponse)
def get_aws_template():
    """Return the current AWS config template.

    Falls back to the system ~/.aws/config if no template has been saved yet.
    """
    if os.path.exists(_TEMPLATE_PATH):
        with open(_TEMPLATE_PATH) as f:
            return TemplateResponse(content=f.read(), is_default=False)
    return TemplateResponse(content=_read_default_template(), is_default=True)


@router.put(
    "/aws-template",
    response_model=TemplateResponse,
    dependencies=[Depends(require_role("super_user"))],
)
def update_aws_template(body: TemplateUpdate):
    """Save the AWS config template (super_user only)."""
    os.makedirs(os.path.dirname(_TEMPLATE_PATH), exist_ok=True)
    with open(_TEMPLATE_PATH, "w") as f:
        f.write(body.content)
    return TemplateResponse(content=body.content, is_default=False)


@router.post(
    "/aws-template/apply/{username}",
    dependencies=[Depends(require_role("super_user"))],
)
def apply_template_to_user(username: str):
    """Copy the saved template to a specific user's AWS config (super_user only).

    Overwrites existing config for that user.
    """
    template_content = (
        _read_template_content()
        if os.path.exists(_TEMPLATE_PATH)
        else _read_default_template()
    )
    if not template_content:
        raise HTTPException(status_code=404, detail="Tidak ada template atau config sistem")

    if "/" in username or ".." in username:
        raise HTTPException(status_code=400, detail="Invalid username")

    user_dir = os.path.expanduser(f"~/.aws/users/{username}")
    os.makedirs(f"{user_dir}/sso/cache", exist_ok=True)

    with open(f"{user_dir}/config", "w") as f:
        f.write(template_content)

    return {"message": f"Template berhasil diterapkan untuk {username}"}


def _read_template_content() -> str:
    with open(_TEMPLATE_PATH) as f:
        return f.read()


# ---------------------------------------------------------------------------
# Per-user config (any authenticated user, only own config)
# ---------------------------------------------------------------------------


@router.get("/my-aws-config", response_model=UserConfigResponse)
def get_my_aws_config(
    current_user: Annotated[TokenPayload, Depends(require_auth)],
):
    """Return the current user's personal AWS config file."""
    path = _user_config_path(current_user.username)
    if os.path.exists(path):
        with open(path) as f:
            content = f.read()
    else:
        # Fall back to template or system config as a starting point
        if os.path.exists(_TEMPLATE_PATH):
            with open(_TEMPLATE_PATH) as f:
                content = f.read()
        else:
            content = _read_default_template()
    return UserConfigResponse(content=content, username=current_user.username)


@router.put("/my-aws-config", response_model=UserConfigResponse)
def update_my_aws_config(
    body: TemplateUpdate,
    current_user: Annotated[TokenPayload, Depends(require_auth)],
):
    """Write the current user's personal AWS config file."""
    username = current_user.username
    user_dir = os.path.expanduser(f"~/.aws/users/{username}")
    os.makedirs(f"{user_dir}/sso/cache", exist_ok=True)
    with open(f"{user_dir}/config", "w") as f:
        f.write(body.content)
    return UserConfigResponse(content=body.content, username=username)
