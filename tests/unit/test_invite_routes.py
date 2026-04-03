from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.domain.services.auth_service import TokenPayload


def test_create_invite_does_not_open_second_db_session(monkeypatch):
    import backend.interfaces.api.dependencies as deps
    from backend.interfaces.api.routes.auth import router as auth_router

    class _FakeInviteService:
        def create_invite(self, *, email: str, role: str, invited_by):
            return SimpleNamespace(
                id="inv-1",
                email=email,
                role=role,
                accepted=False,
                expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
                created_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
            )

    def _require_auth_override():
        return TokenPayload(user_id="user-1", username="admin", role="super_user")

    def _raise_if_called(*args, **kwargs):
        raise RuntimeError("unexpected extra DB session")

    monkeypatch.setattr(
        "backend.infra.database.session.build_session_factory",
        _raise_if_called,
    )

    app = FastAPI()
    app.include_router(auth_router, prefix="/api/v1")
    app.dependency_overrides[deps.get_invite_service] = lambda: _FakeInviteService()
    app.dependency_overrides[deps.require_auth] = _require_auth_override

    client = TestClient(app)
    res = client.post(
        "/api/v1/auth/invites",
        json={"email": "tester@icscompute.com", "role": "user"},
    )

    assert res.status_code == 200
    assert res.json()["email"] == "tester@icscompute.com"
