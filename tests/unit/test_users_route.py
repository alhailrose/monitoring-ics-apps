from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_app(repo_mock):
    from backend.interfaces.api.routes.users import router, _get_repo
    import backend.interfaces.api.dependencies as deps
    from backend.domain.services.auth_service import TokenPayload

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    app.dependency_overrides[_get_repo] = lambda: repo_mock
    app.dependency_overrides[deps.require_auth] = lambda: TokenPayload(
        user_id="u-1", username="admin", role="super_user"
    )
    return app


def test_create_user_commits_session():
    repo = MagicMock()
    repo.get_by_username.return_value = None
    repo.create_user.return_value = SimpleNamespace(
        id="u-2", username="john", role="user", is_active=True
    )

    client = TestClient(_make_app(repo))
    resp = client.post(
        "/api/v1/users",
        json={"username": "john", "password": "password123", "role": "user"},
    )

    assert resp.status_code == 201
    repo.session.commit.assert_called_once()


def test_update_role_commits_session():
    repo = MagicMock()
    repo.update_role.return_value = SimpleNamespace(
        id="u-2", username="john", role="super_user", is_active=True
    )

    client = TestClient(_make_app(repo))
    resp = client.patch("/api/v1/users/u-2/role", json={"role": "super_user"})

    assert resp.status_code == 200
    repo.session.commit.assert_called_once()


def test_deactivate_user_commits_session():
    repo = MagicMock()
    repo.deactivate.return_value = SimpleNamespace(
        id="u-2", username="john", role="user", is_active=False
    )

    client = TestClient(_make_app(repo))
    resp = client.delete("/api/v1/users/u-2")

    assert resp.status_code == 204
    repo.session.commit.assert_called_once()
