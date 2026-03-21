"""Unit + integration tests for /auth/login, /auth/me endpoints,
and for the require_auth / require_role dependencies."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from jose import jwt

from backend.domain.services.auth_service import (
    ALGORITHM,
    AuthService,
    InvalidCredentialsError,
    TokenPayload,
)

_SECRET = "test-secret-for-routes"
_EXPIRE_HOURS = 8


# ---------------------------------------------------------------------------
# Token factory
# ---------------------------------------------------------------------------


def _make_token(user_id="uid-1", username="alice", role="user", expire_delta=None):
    delta = expire_delta if expire_delta is not None else timedelta(hours=_EXPIRE_HOURS)
    payload = {
        "sub": user_id,
        "username": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + delta,
    }
    return jwt.encode(payload, _SECRET, algorithm=ALGORITHM)


# ---------------------------------------------------------------------------
# Shared dependency overrides
# ---------------------------------------------------------------------------


def _require_auth_override(request: Request) -> TokenPayload:
    """Test replacement for require_auth: validates JWT with test secret."""
    from fastapi import HTTPException, status

    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token_str = auth.split(" ", 1)[1].strip()
    try:
        data = jwt.decode(token_str, _SECRET, algorithms=[ALGORITHM])
        return TokenPayload(
            user_id=data["sub"],
            username=data["username"],
            role=data["role"],
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or expired",
        )


# ---------------------------------------------------------------------------
# App factories
# ---------------------------------------------------------------------------


def _make_login_app(auth_svc):
    """Minimal app with /auth/login, auth_service overridden."""
    import backend.interfaces.api.dependencies as deps
    from backend.interfaces.api.routes.auth import router as auth_router

    app = FastAPI()
    app.include_router(auth_router, prefix="/api/v1")
    app.dependency_overrides[deps.get_auth_service] = lambda: auth_svc
    app.dependency_overrides[deps.require_auth] = _require_auth_override
    return app


def _make_me_app():
    """Minimal app with /auth/me, require_auth overridden."""
    import backend.interfaces.api.dependencies as deps
    from backend.interfaces.api.routes.auth import router as auth_router

    app = FastAPI()
    app.include_router(auth_router, prefix="/api/v1")
    app.dependency_overrides[deps.require_auth] = _require_auth_override
    return app


def _make_role_guarded_app():
    """App with a super_user-only route and a read route, require_auth overridden."""
    import backend.interfaces.api.dependencies as deps
    from fastapi import APIRouter, Depends

    router = APIRouter()

    @router.post("/admin-only", dependencies=[Depends(deps.require_role("super_user"))])
    def admin_only():
        return {"ok": True}

    app = FastAPI()
    app.include_router(router, prefix="/test")
    app.dependency_overrides[deps.require_auth] = _require_auth_override
    return app


def _make_customers_app():
    """Customers router with require_auth and customer_service overridden."""
    import backend.interfaces.api.dependencies as deps
    from backend.interfaces.api.routes.customers import router as customers_router

    mock_svc = MagicMock()
    mock_svc.list_customers.return_value = []
    mock_svc.create_customer.return_value = {"id": "new-cust"}

    app = FastAPI()
    app.include_router(customers_router, prefix="/api/v1")
    app.dependency_overrides[deps.get_customer_service] = lambda: mock_svc
    app.dependency_overrides[deps.require_auth] = _require_auth_override
    return app, mock_svc


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------


class TestLoginEndpoint:
    def _mock_svc(self, succeed=True, role="user"):
        svc = MagicMock(spec=AuthService)
        if succeed:
            svc.login.return_value = {
                "access_token": _make_token(role=role),
                "token_type": "bearer",
                "expires_at": (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat(),
            }
        else:
            svc.login.side_effect = InvalidCredentialsError("Invalid username or password")
        return svc

    def test_valid_credentials_returns_200_with_token(self):
        client = TestClient(_make_login_app(self._mock_svc(succeed=True)))
        r = client.post("/api/v1/auth/login", data={"username": "alice", "password": "correct"})
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_at" in data

    def test_wrong_credentials_returns_401(self):
        client = TestClient(_make_login_app(self._mock_svc(succeed=False)))
        r = client.post("/api/v1/auth/login", data={"username": "alice", "password": "bad"})
        assert r.status_code == 401

    def test_error_message_is_generic(self):
        """Must not reveal whether username or password was wrong."""
        client = TestClient(_make_login_app(self._mock_svc(succeed=False)))
        r = client.post("/api/v1/auth/login", data={"username": "ghost", "password": "any"})
        assert r.status_code == 401
        assert "invalid username or password" in r.json()["detail"].lower()

    def test_missing_password_returns_422(self):
        client = TestClient(_make_login_app(self._mock_svc()))
        r = client.post("/api/v1/auth/login", data={"username": "alice"})
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------


class TestMeEndpoint:
    def test_valid_token_returns_user_identity(self):
        token = _make_token(user_id="uid-42", username="bob", role="super_user")
        client = TestClient(_make_me_app())
        r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == "uid-42"
        assert data["username"] == "bob"
        assert data["role"] == "super_user"

    def test_no_token_returns_401(self):
        client = TestClient(_make_me_app())
        r = client.get("/api/v1/auth/me")
        assert r.status_code == 401

    def test_invalid_token_returns_401(self):
        client = TestClient(_make_me_app())
        r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.valid.token"})
        assert r.status_code == 401

    def test_expired_token_returns_401(self):
        expired = _make_token(expire_delta=timedelta(seconds=-1))
        client = TestClient(_make_me_app())
        r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# require_role — super_user vs user access
# ---------------------------------------------------------------------------


class TestRequireRole:
    def test_super_user_can_access_admin_route(self):
        token = _make_token(role="super_user")
        client = TestClient(_make_role_guarded_app())
        r = client.post("/test/admin-only", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200

    def test_user_role_blocked_from_admin_route_with_403(self):
        token = _make_token(role="user")
        client = TestClient(_make_role_guarded_app())
        r = client.post("/test/admin-only", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 403

    def test_missing_token_returns_401(self):
        client = TestClient(_make_role_guarded_app())
        r = client.post("/test/admin-only")
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Role guards on /customers write endpoints
# ---------------------------------------------------------------------------


class TestCustomerRouteRoleGuards:
    _payload = {
        "name": "test-cust",
        "display_name": "Test Customer",
        "checks": [],
        "slack_enabled": False,
    }

    def test_super_user_can_create_customer(self):
        app, _ = _make_customers_app()
        token = _make_token(role="super_user")
        r = TestClient(app).post(
            "/api/v1/customers",
            json=self._payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 201

    def test_user_role_cannot_create_customer(self):
        app, _ = _make_customers_app()
        token = _make_token(role="user")
        r = TestClient(app).post(
            "/api/v1/customers",
            json=self._payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 403

    def test_both_roles_can_list_customers(self):
        app, _ = _make_customers_app()
        for role in ("user", "super_user"):
            token = _make_token(role=role)
            r = TestClient(app).get(
                "/api/v1/customers",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert r.status_code == 200
