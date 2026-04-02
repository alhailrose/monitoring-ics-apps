"""AWS config template management endpoints."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.interfaces.api.dependencies import require_role

router = APIRouter(prefix="/settings", tags=["settings"])

_TEMPLATE_PATH = os.path.expanduser("~/.aws/aws-config.template")

_DEFAULT_TEMPLATE = """\
[profile msmonitoring]
sso_session = msmonitoring
sso_account_id = 123456789012
sso_role_name = AWSReadOnlyAccess
region = ap-southeast-3

[sso-session msmonitoring]
sso_start_url = https://your-sso.awsapps.com/start
sso_region = ap-southeast-1
sso_registration_scopes = sso:account:access
"""


class TemplateResponse(BaseModel):
    content: str
    is_default: bool


class TemplateUpdate(BaseModel):
    content: str


@router.get("/aws-template", response_model=TemplateResponse)
def get_aws_template():
    """Return the current AWS config template."""
    if os.path.exists(_TEMPLATE_PATH):
        with open(_TEMPLATE_PATH) as f:
            return TemplateResponse(content=f.read(), is_default=False)
    return TemplateResponse(content=_DEFAULT_TEMPLATE, is_default=True)


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
    """Copy the saved template to a specific user's AWS config directory.

    Overwrites the user's existing config. Use to provision or reset a user.
    """
    if not os.path.exists(_TEMPLATE_PATH):
        raise HTTPException(status_code=404, detail="Belum ada template yang disimpan")

    # Guard against path traversal
    if "/" in username or ".." in username:
        raise HTTPException(status_code=400, detail="Invalid username")

    user_dir = os.path.expanduser(f"~/.aws/users/{username}")
    os.makedirs(f"{user_dir}/sso/cache", exist_ok=True)

    with open(_TEMPLATE_PATH) as f:
        content = f.read()
    with open(f"{user_dir}/config", "w") as f:
        f.write(content)

    return {"message": f"Template berhasil diterapkan untuk {username}"}
