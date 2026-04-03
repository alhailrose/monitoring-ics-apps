from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_app(repo_mock):
    from backend.interfaces.api.routes.tickets import router, _get_repo
    import backend.interfaces.api.dependencies as deps
    from backend.domain.services.auth_service import TokenPayload

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[_get_repo] = lambda: repo_mock
    app.dependency_overrides[deps.require_auth] = lambda: TokenPayload(
        user_id="u-1", username="admin", role="super_user"
    )
    return app


def test_create_ticket_generates_ticket_number_and_commits():
    repo = MagicMock()
    repo.next_ticket_number.return_value = "TKT-0001"
    repo.create_ticket.return_value = SimpleNamespace(
        id="t-1",
        ticket_no="TKT-0001",
        task="Investigate CPU alarm",
        pic="Bagus",
        status="open",
        description_solution="Initial triage",
        created_at=datetime(2026, 4, 3, tzinfo=timezone.utc),
        ended_at=None,
    )

    client = TestClient(_make_app(repo))
    resp = client.post(
        "/api/v1/tickets",
        json={
            "task": "Investigate CPU alarm",
            "pic": "Bagus",
            "status": "open",
            "description_solution": "Initial triage",
        },
    )

    assert resp.status_code == 201
    assert resp.json()["ticket_no"] == "TKT-0001"
    repo.session.commit.assert_called_once()


def test_update_ticket_sets_ended_at_when_resolved():
    repo = MagicMock()
    repo.update_ticket.return_value = SimpleNamespace(
        id="t-1",
        ticket_no="TKT-0001",
        task="Investigate CPU alarm",
        pic="Bagus",
        status="resolved",
        description_solution="Threshold tuned",
        created_at=datetime(2026, 4, 3, tzinfo=timezone.utc),
        ended_at=datetime(2026, 4, 3, 10, tzinfo=timezone.utc),
    )

    client = TestClient(_make_app(repo))
    resp = client.patch(
        "/api/v1/tickets/t-1",
        json={
            "status": "resolved",
            "description_solution": "Threshold tuned",
        },
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"
    assert resp.json()["ended_at"] is not None
    repo.session.commit.assert_called_once()
