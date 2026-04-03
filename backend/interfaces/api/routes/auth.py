"""Auth endpoints — login, Google OAuth, invites, and current user."""

from __future__ import annotations

from datetime import timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

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
    email: str
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


@router.post(
    "/login", response_model=TokenResponse, summary="Login and obtain JWT token"
)
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


@router.get(
    "/me", response_model=UserMeResponse, summary="Get current authenticated user"
)
def me(current_user: Annotated[TokenPayload, Depends(require_auth)]):
    """Return the current session's user identity and role decoded from the JWT."""
    return UserMeResponse(
        id=current_user.user_id,
        username=current_user.username,
        role=current_user.role,
    )


@router.post(
    "/google", response_model=TokenResponse, summary="Login with Google OAuth id_token"
)
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
):
    """First Google login after receiving an invite — creates the user account.

    Uses a single DB session so the newly created user is visible to login_google.
    """
    import json
    import base64
    from backend.config.settings import get_settings
    from backend.infra.database.session import build_session_factory
    from backend.infra.database.repositories.user_repository import UserRepository
    from backend.infra.database.repositories.invite_repository import InviteRepository
    from backend.domain.services.invite_service import InviteService as _InviteService
    from backend.domain.services.auth_service import AuthService as _AuthService

    settings = get_settings()

    # Decode id_token payload (without verification) to extract email/sub for invite check
    try:
        parts = body.id_token.split(".")
        padded = parts[1] + "=" * (4 - len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(padded))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid token format")

    google_sub = claims.get("sub", "")
    email = claims.get("email", "")
    hd = claims.get("hd", "")

    if not email.endswith("@icscompute.com") and hd != "icscompute.com":
        raise HTTPException(
            status_code=403, detail="Only @icscompute.com accounts allowed"
        )

    # Use a single session so the created user is visible to login_google
    session = build_session_factory(settings.database_url)()
    try:
        user_repo = UserRepository(session)
        invite_repo = InviteRepository(session)
        svc = _InviteService(
            invite_repo=invite_repo,
            user_repo=user_repo,
            smtp_host=settings.smtp_host,
            smtp_port=settings.smtp_port,
            smtp_user=settings.smtp_user,
            smtp_password=settings.smtp_password,
            smtp_from=settings.smtp_from,
            app_base_url=settings.app_base_url,
            invite_expire_hours=settings.invite_expire_hours,
        )
        try:
            svc.accept_invite(token=invite_token, google_sub=google_sub, email=email)
        except InviteError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        # Commit so login_google (same session) can find the new user
        session.commit()

        auth_svc = _AuthService(
            user_repo=user_repo,
            jwt_secret=settings.jwt_secret,
            jwt_expire_hours=settings.jwt_expire_hours,
        )
        try:
            return auth_svc.login_google(body.id_token, settings.google_client_id)
        except Exception:
            raise HTTPException(
                status_code=500, detail="Account created but login failed"
            )
    finally:
        session.close()


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
    inviter = TokenPayload(
        user_id=current_user.user_id,
        username=current_user.username,
        role=current_user.role,
    )
    try:
        invite = invite_svc.create_invite(
            email=str(body.email),
            role=body.role,
            invited_by=inviter,
        )
    except InviteError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return InviteResponse(
        id=invite.id,
        email=invite.email,
        role=invite.role,
        accepted=invite.accepted,
        expires_at=invite.expires_at.isoformat(),
        created_at=invite.created_at.isoformat(),
    )


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
