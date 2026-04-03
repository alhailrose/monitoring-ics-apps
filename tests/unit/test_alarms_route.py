from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_app(executor_mock):
    from backend.interfaces.api.routes.alarms import router
    import backend.interfaces.api.dependencies as deps
    from backend.domain.services.auth_service import TokenPayload

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[deps.get_check_executor] = lambda: executor_mock
    app.dependency_overrides[deps.require_auth] = lambda: TokenPayload(
        user_id="u-1", username="admin", role="super_user"
    )
    return app


def test_verify_alarm_executes_alarm_verification_for_mapped_accounts():
    executor = MagicMock()
    executor.customer_repo.list_customers.return_value = [
        SimpleNamespace(
            id="cust-1",
            accounts=[
                SimpleNamespace(id="acc-1", is_active=True, alarm_names=["High CPU"]),
                SimpleNamespace(id="acc-2", is_active=True, alarm_names=["Disk Full"]),
            ],
        ),
        SimpleNamespace(
            id="cust-2",
            accounts=[
                SimpleNamespace(id="acc-3", is_active=True, alarm_names=["High CPU"]),
            ],
        ),
    ]
    executor.execute.return_value = {
        "check_runs": [
            {"customer_id": "cust-1", "check_run_id": "run-1", "slack_sent": False}
        ],
        "execution_time_seconds": 1.2,
        "results": [
            {"account": {"id": "acc-1"}, "status": "ALARM"},
            {"account": {"id": "acc-3"}, "status": "OK"},
        ],
        "consolidated_outputs": {},
    }

    client = TestClient(_make_app(executor))
    resp = client.post("/api/v1/alarms/High%20CPU/verify")

    assert resp.status_code == 200
    body = resp.json()
    assert body["alarm_name"] == "High CPU"
    assert body["counts"]["ALARM"] == 1
    assert body["counts"]["OK"] == 1

    kwargs = executor.execute.call_args.kwargs
    assert kwargs["mode"] == "single"
    assert kwargs["check_name"] == "alarm_verification"
    assert set(kwargs["customer_ids"]) == {"cust-1", "cust-2"}
    assert set(kwargs["account_ids"]) == {"acc-1", "acc-3"}
    assert kwargs["check_params"]["account_alarm_names"] == {
        "acc-1": ["High CPU"],
        "acc-3": ["High CPU"],
    }


def test_verify_alarm_returns_404_if_not_mapped():
    executor = MagicMock()
    executor.customer_repo.list_customers.return_value = [
        SimpleNamespace(
            id="cust-1",
            accounts=[
                SimpleNamespace(id="acc-1", is_active=True, alarm_names=["Disk Full"]),
            ],
        )
    ]

    client = TestClient(_make_app(executor))
    resp = client.post("/api/v1/alarms/High%20CPU/verify")

    assert resp.status_code == 404
    assert "termapping" in resp.json()["detail"]
