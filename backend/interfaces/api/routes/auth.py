"""Auth endpoints — login, Google OAuth, invites, and current user."""

from __future__ import annotations

from datetime import timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr

from backend.interfaces.api.dependencies import (
    get_auth_service,
    get_invite_service,
    require_auth,
    require_role,
)
from backend.domain.services.auth_service import (
    DomainNotAllowedError,
    InvalidCredentialsError,
    InvalidTokenError,
    InviteRequiredError,
    TokenPayload,
)
from backend.domain.services.invite_service import InviteError

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_at: str


class UserMeResponse(BaseModel):
    id: str
    username: str
    role: str


class GoogleLoginRequest(BaseModel):
    id_token: str


class InviteRequest(BaseModel):
    email: EmailStr
    role: str = "user"


class InviteResponse(BaseModel):
    id: str
    email: str
    role: str
    accepted: bool
    expires_at: str
    created_at: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/login", response_model=TokenResponse, summary="Login and obtain JWT token")
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_svc=Depends(get_auth_service),
):
    """Authenticate with username + password and receive a JWT access token.

    Returns HTTP 401 on any credential failure — does not distinguish
    between unknown username and wrong password to prevent user enumeration.
    """
    try:
        result = auth_svc.login(form.username, form.password)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return result


@router.get("/me", response_model=UserMeResponse, summary="Get current authenticated user")
def me(current_user: Annotated[TokenPayload, Depends(require_auth)]):
    """Return the current session's user identity and role decoded from the JWT."""
    return UserMeResponse(
        id=current_user.user_id,
        username=current_user.username,
        role=current_user.role,
    )


@router.post("/google", response_model=TokenResponse, summary="Login with Google OAuth id_token")
def login_google(
    body: GoogleLoginRequest,
    auth_svc=Depends(get_auth_service),
):
    """Verify a Google id_token and return a signed JWT if the user has an accepted invite."""
    from backend.config.settings import get_settings
    settings = get_settings()
    try:
        return auth_svc.login_google(body.id_token, settings.google_client_id)
    except DomainNotAllowedError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except InviteRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="invite_required",
            headers={"X-Error": str(exc)},
        )
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))


@router.post(
    "/google/accept-invite",
    response_model=TokenResponse,
    summary="Accept invite and login with Google id_token",
)
def accept_invite_google(
    body: GoogleLoginRequest,
    invite_token: str,
    auth_svc=Depends(get_auth_service),
    invite_svc=Depends(get_invite_service),
):
    """First Google login after receiving an invite — creates the user account."""
    from backend.config.settings import get_settings
    import json, base64

    settings = get_settings()
    try:
        from jose import jwt as jose_jwt
        jwks_data = auth_svc._repo  # noqa: SLF001 — access only to get settings
        # Decode without verification to extract claims (verification happens below)
        parts = body.id_token.split(".")
        padded = parts[1] + "=" * (4 - len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(padded))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid token format")

    google_sub = claims.get("sub", "")
    email = claims.get("email", "")
    hd = claims.get("hd", "")

    if not email.endswith("@icscompute.com") and hd != "icscompute.com":
        raise HTTPException(status_code=403, detail="Only @icscompute.com accounts allowed")

    try:
        invite_svc.accept_invite(token=invite_token, google_sub=google_sub, email=email)
    except InviteError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Now login normally
    try:
        return auth_svc.login_google(body.id_token, settings.google_client_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Account created but login failed")


@router.post(
    "/invites",
    response_model=InviteResponse,
    summary="Send invite email (super_user only)",
    dependencies=[Depends(require_role("super_user"))],
)
def create_invite(
    body: InviteRequest,
    current_user: Annotated[TokenPayload, Depends(require_auth)],
    invite_svc=Depends(get_invite_service),
):
    from backend.infra.database.session import build_session_factory
    from backend.config.settings import get_settings
    from backend.infra.database.repositories.user_repository import UserRepository

    session = build_session_factory(get_settings().database_url)()
    try:
        inviter = UserRepository(session).get_by_id(current_user.user_id)
        if not inviter:
            raise HTTPException(status_code=404, detail="Inviter user not found")
        try:
            invite = invite_svc.create_invite(
                email=str(body.email),
                role=body.role,
                invited_by=inviter,
            )
        except InviteError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        session.commit()
        return InviteResponse(
            id=invite.id,
            email=invite.email,
            role=invite.role,
            accepted=invite.accepted,
            expires_at=invite.expires_at.isoformat(),
            created_at=invite.created_at.isoformat(),
        )
    finally:
        session.close()


@router.get(
    "/invites",
    response_model=list[InviteResponse],
    summary="List all invites (super_user only)",
    dependencies=[Depends(require_role("super_user"))],
)
def list_invites(invite_svc=Depends(get_invite_service)):
    invites = invite_svc._invites.list_all()  # noqa: SLF001
    return [
        InviteResponse(
            id=i.id,
            email=i.email,
            role=i.role,
            accepted=i.accepted,
            expires_at=i.expires_at.isoformat(),
            created_at=i.created_at.isoformat(),
        )
        for i in invites
    ]
