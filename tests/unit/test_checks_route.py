import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock


def _make_app(executor_mock):
    from fastapi import FastAPI
    from backend.interfaces.api.routes.checks import router
    import backend.interfaces.api.dependencies as deps

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[deps.get_check_executor] = lambda: executor_mock
    return app


def test_execute_accepts_customer_ids_list():
    """POST /api/v1/checks/execute should accept customer_ids as a list."""
    mock_executor = MagicMock()
    mock_executor.execute.return_value = {
        "check_runs": [
            {"customer_id": "cust-1", "check_run_id": "run-1", "slack_sent": False}
        ],
        "execution_time_seconds": 1.0,
        "results": [],
        "consolidated_outputs": {"cust-1": "report"},
    }
    client = TestClient(_make_app(mock_executor))

    r = client.post(
        "/api/v1/checks/execute",
        json={
            "customer_ids": ["cust-1"],
            "mode": "all",
            "send_slack": False,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert "check_runs" in data
    assert data["check_runs"][0]["customer_id"] == "cust-1"
    assert "customer_labels" in data


def test_execute_rejects_empty_customer_ids():
    """customer_ids must have at least one item."""
    mock_executor = MagicMock()
    client = TestClient(_make_app(mock_executor))

    r = client.post(
        "/api/v1/checks/execute",
        json={
            "customer_ids": [],
            "mode": "all",
            "send_slack": False,
        },
    )
    assert r.status_code == 422  # Pydantic validation error


def test_execute_accepts_legacy_customer_id_field():
    """Old customer_id field remains supported via compatibility layer."""
    mock_executor = MagicMock()
    mock_executor.execute.return_value = {
        "check_runs": [
            {"customer_id": "cust-1", "check_run_id": "run-1", "slack_sent": False}
        ],
        "execution_time_seconds": 1.0,
        "results": [],
        "consolidated_outputs": {"cust-1": "report"},
    }
    client = TestClient(_make_app(mock_executor))

    r = client.post(
        "/api/v1/checks/execute",
        json={
            "customer_id": "cust-1",  # old field — no longer valid
            "mode": "all",
            "send_slack": False,
        },
    )
    assert r.status_code == 200
    mock_executor.execute.assert_called_once()
    kwargs = mock_executor.execute.call_args.kwargs
    assert kwargs["customer_ids"] == ["cust-1"]


def test_execute_rejects_blank_customer_id():
    """customer_ids items must not be blank strings."""
    mock_executor = MagicMock()
    client = TestClient(_make_app(mock_executor))

    r = client.post(
        "/api/v1/checks/execute",
        json={
            "customer_ids": [""],
            "mode": "all",
            "send_slack": False,
        },
    )
    assert r.status_code == 422


def test_execute_rejects_duplicate_customer_ids():
    """customer_ids must not contain duplicates."""
    mock_executor = MagicMock()
    client = TestClient(_make_app(mock_executor))

    r = client.post(
        "/api/v1/checks/execute",
        json={
            "customer_ids": ["cust-1", "cust-1"],
            "mode": "all",
            "send_slack": False,
        },
    )
    assert r.status_code == 422


def test_execute_single_mode_requires_check_name():
    mock_executor = MagicMock()
    client = TestClient(_make_app(mock_executor))

    r = client.post(
        "/api/v1/checks/execute",
        json={
            "customer_ids": ["cust-1"],
            "mode": "single",
            "send_slack": False,
        },
    )
    assert r.status_code == 400


def test_async_execute_endpoint_is_not_available():
    """Background job execution endpoint is removed; sync execute is canonical."""
    mock_executor = MagicMock()
    client = TestClient(_make_app(mock_executor))

    r = client.post(
        "/api/v1/checks/execute/async",
        json={
            "customer_ids": ["cust-1"],
            "mode": "all",
            "send_slack": False,
        },
    )
    assert r.status_code == 404


@pytest.mark.parametrize("path", ["/api/v1/checks/jobs", "/api/v1/checks/jobs/job-123"])
def test_async_job_endpoints_are_not_available(path: str):
    """Job polling/list endpoints are removed with async execution flow."""
    mock_executor = MagicMock()
    client = TestClient(_make_app(mock_executor))

    r = client.get(path)
    assert r.status_code == 404
