"""Application auth service — password hashing and JWT lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from backend.infra.database.repositories.user_repository import UserRepository

ALGORITHM = "HS256"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class InvalidCredentialsError(Exception):
    """Raised when username/password pair is invalid or user is inactive."""


class InvalidTokenError(Exception):
    """Raised when a JWT is missing, malformed, expired, or tampered."""


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
