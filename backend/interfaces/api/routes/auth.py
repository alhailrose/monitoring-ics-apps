"""Auth endpoints — login and current user."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from backend.interfaces.api.dependencies import get_auth_service, require_auth
from backend.domain.services.auth_service import InvalidCredentialsError, TokenPayload

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
