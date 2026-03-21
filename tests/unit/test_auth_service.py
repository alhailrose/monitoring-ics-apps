"""Unit tests for AuthService — login, JWT issuance, and token validation."""

from datetime import timedelta, timezone, datetime
from unittest.mock import MagicMock

import pytest
from jose import jwt

from backend.domain.services.auth_service import (
    ALGORITHM,
    AuthService,
    InvalidCredentialsError,
    InvalidTokenError,
    TokenPayload,
    hash_password,
    verify_password,
)


# ---------------------------------------------------------------------------
# Password utilities
# ---------------------------------------------------------------------------


def test_hash_and_verify_round_trip():
    plain = "secretpassword"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)


def test_verify_wrong_password():
    hashed = hash_password("correct")
    assert not verify_password("wrong", hashed)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SECRET = "test-secret-key"
_EXPIRE_HOURS = 8


def _make_service(user=None):
    repo = MagicMock()
    repo.get_by_username.return_value = user
    return AuthService(user_repo=repo, jwt_secret=_SECRET, jwt_expire_hours=_EXPIRE_HOURS)


def _make_user(username="alice", role="user", is_active=True):
    user = MagicMock()
    user.id = "user-uuid-1"
    user.username = username
    user.hashed_password = hash_password("correct-pass")
    user.role = role
    user.is_active = is_active
    return user


# ---------------------------------------------------------------------------
# AuthService.login — success path
# ---------------------------------------------------------------------------


def test_login_returns_token_response():
    svc = _make_service(user=_make_user())
    result = svc.login("alice", "correct-pass")
    assert "access_token" in result
    assert result["token_type"] == "bearer"
    assert "expires_at" in result


def test_login_token_contains_correct_payload():
    user = _make_user(username="bob", role="super_user")
    svc = _make_service(user=user)
    result = svc.login("bob", "correct-pass")
    data = jwt.decode(result["access_token"], _SECRET, algorithms=[ALGORITHM])
    assert data["sub"] == user.id
    assert data["username"] == "bob"
    assert data["role"] == "super_user"


# ---------------------------------------------------------------------------
# AuthService.login — failure paths
# ---------------------------------------------------------------------------


def test_login_wrong_password_raises():
    svc = _make_service(user=_make_user())
    with pytest.raises(InvalidCredentialsError) as exc_info:
        svc.login("alice", "wrong-pass")
    # Error message must not distinguish password vs username
    assert "username or password" in str(exc_info.value).lower()


def test_login_unknown_username_raises():
    svc = _make_service(user=None)
    with pytest.raises(InvalidCredentialsError) as exc_info:
        svc.login("unknown", "any-pass")
    assert "username or password" in str(exc_info.value).lower()


def test_login_same_error_message_for_both_failures():
    """Wrong password and unknown username must produce identical messages (no enumeration)."""
    svc_wrong_pass = _make_service(user=_make_user())
    svc_unknown = _make_service(user=None)

    try:
        svc_wrong_pass.login("alice", "bad")
    except InvalidCredentialsError as e:
        msg_wrong_pass = str(e)

    try:
        svc_unknown.login("ghost", "bad")
    except InvalidCredentialsError as e:
        msg_unknown = str(e)

    assert msg_wrong_pass == msg_unknown


def test_login_inactive_user_raises():
    inactive = _make_user(is_active=False)
    svc = _make_service(user=inactive)
    with pytest.raises(InvalidCredentialsError):
        svc.login("alice", "correct-pass")


# ---------------------------------------------------------------------------
# AuthService.decode_token — valid tokens
# ---------------------------------------------------------------------------


def test_decode_token_valid():
    user = _make_user(role="super_user")
    svc = _make_service(user=user)
    token_resp = svc.login("alice", "correct-pass")
    payload = svc.decode_token(token_resp["access_token"])
    assert isinstance(payload, TokenPayload)
    assert payload.user_id == user.id
    assert payload.username == "alice"
    assert payload.role == "super_user"


# ---------------------------------------------------------------------------
# AuthService.decode_token — invalid tokens
# ---------------------------------------------------------------------------


def test_decode_expired_token_raises():
    # Manually craft a token that expired in the past
    payload = {
        "sub": "uid-1",
        "username": "alice",
        "role": "user",
        "exp": datetime(2000, 1, 1, tzinfo=timezone.utc),
    }
    expired_token = jwt.encode(payload, _SECRET, algorithm=ALGORITHM)
    svc = _make_service()
    with pytest.raises(InvalidTokenError):
        svc.decode_token(expired_token)


def test_decode_tampered_signature_raises():
    user = _make_user()
    svc = _make_service(user=user)
    token_resp = svc.login("alice", "correct-pass")
    tampered = token_resp["access_token"][:-4] + "AAAA"
    with pytest.raises(InvalidTokenError):
        svc.decode_token(tampered)


def test_decode_wrong_secret_raises():
    payload = {
        "sub": "uid-1",
        "username": "alice",
        "role": "user",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    token = jwt.encode(payload, "different-secret", algorithm=ALGORITHM)
    svc = _make_service()
    with pytest.raises(InvalidTokenError):
        svc.decode_token(token)


def test_decode_missing_payload_fields_raises():
    # Token missing required fields
    incomplete = jwt.encode(
        {"sub": "uid-1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
        _SECRET,
        algorithm=ALGORITHM,
    )
    svc = _make_service()
    with pytest.raises(InvalidTokenError):
        svc.decode_token(incomplete)
