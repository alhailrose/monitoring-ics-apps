"""Application auth service — password hashing and JWT lifecycle."""

from __future__ import annotations

import json
import time
import urllib.request
from base64 import urlsafe_b64decode
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from backend.infra.database.repositories.user_repository import UserRepository

ALGORITHM = "HS256"
_GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_ALLOWED_DOMAIN = "icscompute.com"

# Simple in-memory JWKS cache (key: url, value: (certs_dict, fetched_at))
_jwks_cache: dict[str, tuple[dict, float]] = {}


def _fetch_google_public_keys() -> dict:
    cache = _jwks_cache.get(_GOOGLE_CERTS_URL)
    if cache and time.time() - cache[1] < 3600:
        return cache[0]
    with urllib.request.urlopen(_GOOGLE_CERTS_URL, timeout=10) as resp:
        data = json.loads(resp.read())
    _jwks_cache[_GOOGLE_CERTS_URL] = (data, time.time())
    return data


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class InvalidCredentialsError(Exception):
    """Raised when username/password pair is invalid or user is inactive."""


class InvalidTokenError(Exception):
    """Raised when a JWT is missing, malformed, expired, or tampered."""


class DomainNotAllowedError(Exception):
    """Raised when Google account is not from the allowed domain."""


class InviteRequiredError(Exception):
    """Raised when user has no accepted invite."""


# ---------------------------------------------------------------------------
# Password utilities (module-level so seed scripts can import them directly)
# ---------------------------------------------------------------------------


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ---------------------------------------------------------------------------
# Token payload
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TokenPayload:
    user_id: str
    username: str
    role: str


# ---------------------------------------------------------------------------
# AuthService
# ---------------------------------------------------------------------------


class AuthService:
    def __init__(self, user_repo: UserRepository, jwt_secret: str, jwt_expire_hours: int):
        self._repo = user_repo
        self._secret = jwt_secret
        self._expire_hours = jwt_expire_hours

    # -- Login --

    def login(self, username: str, password: str) -> dict:
        """Validate credentials and return a signed JWT token response.

        Raises:
            InvalidCredentialsError: if the username does not exist, the
                password is wrong, or the user account is inactive.
                (Never distinguish between wrong username and wrong password
                in the error message — prevents user enumeration.)
        """
        user = self._repo.get_by_username(username)
        if not user or not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError("Invalid username or password")
        if not user.is_active:
            raise InvalidCredentialsError("Invalid username or password")

        expires_at = datetime.now(timezone.utc) + timedelta(hours=self._expire_hours)
        payload = {
            "sub": user.id,
            "username": user.username,
            "role": user.role,
            "exp": expires_at,
        }
        token = jwt.encode(payload, self._secret, algorithm=ALGORITHM)
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_at": expires_at.isoformat(),
        }

    # -- Google OAuth login --

    def login_google(self, id_token: str, google_client_id: str) -> dict:
        """Verify a Google id_token and return a signed JWT response.

        Raises:
            DomainNotAllowedError: if the account is not @icscompute.com
            InviteRequiredError: if no accepted invite exists for this email
        """
        try:
            jwks = _fetch_google_public_keys()
            payload = jwt.decode(
                id_token,
                jwks,
                algorithms=["RS256"],
                audience=google_client_id,
            )
        except Exception as exc:
            raise InvalidTokenError("Invalid Google token") from exc

        hd = payload.get("hd", "")
        email: str = payload.get("email", "")
        if hd != _ALLOWED_DOMAIN and not email.endswith(f"@{_ALLOWED_DOMAIN}"):
            raise DomainNotAllowedError(f"Only @{_ALLOWED_DOMAIN} accounts are allowed")

        google_sub: str = payload.get("sub", "")

        # Look up user by google_sub first, then by email
        user = self._repo.get_by_google_sub(google_sub) or self._repo.get_by_email(email)
        if not user or not user.is_active:
            raise InviteRequiredError("No active account. Ask an admin for an invite.")

        expires_at = datetime.now(timezone.utc) + timedelta(hours=self._expire_hours)
        token_payload = {
            "sub": user.id,
            "username": user.username,
            "role": user.role,
            "exp": expires_at,
        }
        token = jwt.encode(token_payload, self._secret, algorithm=ALGORITHM)
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_at": expires_at.isoformat(),
        }

    # -- Token validation --

    def decode_token(self, token: str) -> TokenPayload:
        """Decode and validate a JWT, returning the token payload.

        Raises:
            InvalidTokenError: if the token is missing, expired, or tampered.
        """
        try:
            data = jwt.decode(token, self._secret, algorithms=[ALGORITHM])
        except JWTError as exc:
            raise InvalidTokenError("Token is invalid or expired") from exc

        user_id = data.get("sub")
        username = data.get("username")
        role = data.get("role")
        if not user_id or not username or not role:
            raise InvalidTokenError("Token payload is incomplete")

        return TokenPayload(user_id=user_id, username=username, role=role)
