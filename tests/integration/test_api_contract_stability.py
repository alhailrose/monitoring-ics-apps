from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient


class _FakeExecutor:
    def execute(self, **_kwargs):
        return {
            "check_runs": [
                {
                    "customer_id": "cust-1",
                    "check_run_id": "run-1",
                    "slack_sent": False,
                }
            ],
            "execution_time_seconds": 1.23,
            "results": [
                {
                    "customer_id": "cust-1",
                    "account": {
                        "id": "acc-1",
                        "profile_name": "connect-prod",
                        "display_name": "Connect Prod",
                    },
                    "check_name": "guardduty",
                    "status": "OK",
                    "summary": "No findings",
                    "output": "No findings",
                }
            ],
            "consolidated_outputs": {"cust-1": "No findings"},
            "backup_overviews": {},
        }


class _FakeCheckRepository:
    def list_history(self, **_kwargs):
        run = SimpleNamespace(
            id="run-1",
            check_mode="single",
            check_name="guardduty",
            created_at=datetime(2026, 3, 19, 10, 0, tzinfo=timezone.utc),
            execution_time_seconds=1.23,
            slack_sent=False,
            results=[SimpleNamespace(status="OK")],
        )
        return [run], 1

    def get_check_run(self, check_run_id):
        account = SimpleNamespace(
            id="acc-1",
            profile_name="connect-prod",
            display_name="Connect Prod",
        )
        customer = SimpleNamespace(
            id="cust-1",
            name="aryanoble",
            display_name="Aryanoble",
        )
        result = SimpleNamespace(
            account=account,
            check_name="guardduty",
            status="OK",
            summary="No findings",
            output="No findings",
            details={"status": "success"},
            created_at=datetime(2026, 3, 19, 10, 1, tzinfo=timezone.utc),
        )
        return SimpleNamespace(
            id=check_run_id,
            customer=customer,
            check_mode="single",
            check_name="guardduty",
            created_at=datetime(2026, 3, 19, 10, 0, tzinfo=timezone.utc),
            execution_time_seconds=1.23,
            slack_sent=False,
            results=[result],
        )

    def list_findings(self, **_kwargs):
        account = SimpleNamespace(
            id="acc-1",
            profile_name="connect-prod",
            display_name="Connect Prod",
        )
        finding = SimpleNamespace(
            id="fe-1",
            check_run_id="run-1",
            account=account,
            check_name="guardduty",
            finding_key="gd:1",
            severity="HIGH",
            title="Privilege escalation",
            description="Suspicious iam activity",
            created_at=datetime(2026, 3, 19, 10, 2, tzinfo=timezone.utc),
        )
        return [finding], 1

    def list_metric_samples(self, **_kwargs):
        account = SimpleNamespace(
            id="acc-1",
            profile_name="connect-prod",
            display_name="Connect Prod",
        )
        sample = SimpleNamespace(
            id="ms-1",
            check_run_id="run-1",
            account=account,
            check_name="daily-arbel",
            metric_name="CPUUtilization",
            metric_status="warn",
            value_num=88.0,
            unit="Percent",
            resource_role="writer",
            resource_id="db-1",
            resource_name="db-1",
            service_type="rds",
            section_name="Primary",
            created_at=datetime(2026, 3, 19, 10, 3, tzinfo=timezone.utc),
        )
        return [sample], 1

    def get_dashboard_summary(self, customer_id, window_hours=24):
        return {
            "customer_id": customer_id,
            "window_hours": window_hours,
            "generated_at": datetime(2026, 3, 19, 10, 10, tzinfo=timezone.utc),
            "since": datetime(2026, 3, 18, 10, 10, tzinfo=timezone.utc),
            "runs": {
                "total": 3,
                "single": 2,
                "all": 1,
                "arbel": 0,
                "latest_created_at": datetime(2026, 3, 19, 10, 5, tzinfo=timezone.utc),
            },
            "results": {
                "total": 5,
                "ok": 4,
                "warn": 1,
                "error": 0,
                "alarm": 0,
                "no_data": 0,
            },
            "findings": {"total": 1, "by_severity": {"HIGH": 1}},
            "metrics": {"total": 1, "by_status": {"warn": 1}},
            "top_checks": [{"check_name": "guardduty", "runs": 2}],
        }


def test_api_contract_stability_for_runs_findings_metrics_dashboard():
    import backend.interfaces.api.dependencies as deps
    from backend.interfaces.api.main import create_app

    app = create_app()
    app.dependency_overrides[deps.get_check_executor] = lambda: _FakeExecutor()
    app.dependency_overrides[deps.get_check_repository] = lambda: _FakeCheckRepository()
    client = TestClient(app)

    execute_resp = client.post(
        "/api/v1/checks/execute",
        json={
            "customer_ids": ["cust-1"],
            "mode": "single",
            "check_name": "guardduty",
        },
    )
    assert execute_resp.status_code == 200
    execute_body = execute_resp.json()
    assert "check_runs" in execute_body
    assert "results" in execute_body
    assert "consolidated_outputs" in execute_body

    history_resp = client.get("/api/v1/history?customer_id=cust-1")
    assert history_resp.status_code == 200
    history_body = history_resp.json()
    assert "total" in history_body
    assert "items" in history_body
    assert "results_summary" in history_body["items"][0]

    run_detail_resp = client.get("/api/v1/history/run-1")
    assert run_detail_resp.status_code == 200
    run_detail_body = run_detail_resp.json()
    assert "customer" in run_detail_body
    assert "results" in run_detail_body

    findings_resp = client.get("/api/v1/findings?customer_id=cust-1")
    assert findings_resp.status_code == 200
    findings_body = findings_resp.json()
    assert "total" in findings_body
    assert "items" in findings_body
    assert "account" in findings_body["items"][0]

    metrics_resp = client.get("/api/v1/metrics?customer_id=cust-1")
    assert metrics_resp.status_code == 200
    metrics_body = metrics_resp.json()
    assert "total" in metrics_body
    assert "items" in metrics_body
    assert metrics_body["items"][0]["metric_name"] == "CPUUtilization"

    dashboard_resp = client.get("/api/v1/dashboard/summary?customer_id=cust-1")
    assert dashboard_resp.status_code == 200
    dashboard_body = dashboard_resp.json()
    assert dashboard_body["customer_id"] == "cust-1"
    assert "runs" in dashboard_body
    assert "results" in dashboard_body
    assert "findings" in dashboard_body
    assert "metrics" in dashboard_body
    assert "top_checks" in dashboard_body
