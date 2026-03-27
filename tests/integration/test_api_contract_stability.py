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
    def list_history_summary(self, **kwargs):
        item = {
            "check_run_id": "run-1",
            "customer": {
                "id": "cust-1",
                "name": "aryanoble",
                "display_name": "Aryanoble",
            },
            "check_mode": "single",
            "check_name": "guardduty",
            "created_at": datetime(2026, 3, 19, 10, 0, tzinfo=timezone.utc).isoformat(),
            "execution_time_seconds": 1.23,
            "slack_sent": False,
            "results_summary": {"total": 1, "ok": 1, "warn": 0, "error": 0},
        }
        return [item], 1

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
            customer_id="cust-1",
            customer=customer,
            check_mode="single",
            check_name="guardduty",
            created_at=datetime(2026, 3, 19, 10, 0, tzinfo=timezone.utc),
            execution_time_seconds=1.23,
            slack_sent=False,
            results=[result],
        )

    def list_findings(self, **_kwargs):
        customer = SimpleNamespace(id="cust-1", display_name="Aryanoble")
        account = SimpleNamespace(
            id="acc-1",
            profile_name="connect-prod",
            display_name="Connect Prod",
            customer=customer,
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
            status="active",
            created_at=datetime(2026, 3, 19, 10, 2, tzinfo=timezone.utc),
            last_seen_at=datetime(2026, 3, 19, 10, 2, tzinfo=timezone.utc),
            resolved_at=None,
        )
        return [finding], 1

    def list_metric_samples(self, **_kwargs):
        customer = SimpleNamespace(id="cust-1", display_name="Aryanoble")
        account = SimpleNamespace(
            id="acc-1",
            profile_name="connect-prod",
            display_name="Connect Prod",
            customer=customer,
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

    def get_workload_monthly_report(
        self,
        customer_id,
        year=None,
        month=None,
        target_runs_per_day=2,
        stuck_days_threshold=7,
    ):
        return {
            "customer_id": customer_id,
            "month": f"{year or 2026:04d}-{month or 3:02d}",
            "target_runs_per_day": target_runs_per_day,
            "days_in_month": 31,
            "days_considered": 26,
            "coverage": {
                "total_runs": 40,
                "expected_runs": 52,
                "completion_rate": 76.92,
                "days_met_target": 18,
                "days_missing_target": 8,
            },
            "daily_runs": [{"date": "2026-03-01", "runs": 2}],
            "top_missing_days": [{"date": "2026-03-05", "runs": 1}],
            "metric_fluctuations": [
                {
                    "metric_name": "cpu_utilization",
                    "sample_count": 40,
                    "days_with_samples": 20,
                    "avg_value": 42.3,
                    "min_value": 11.0,
                    "max_value": 88.0,
                    "daily_avg_range": 21.4,
                }
            ],
            "metric_daily_series": [
                {
                    "metric_name": "cpu_utilization",
                    "daily_avg_range": 21.4,
                    "points": [
                        {"date": "2026-03-01", "avg_value": 35.0, "max_value": 60.0},
                        {"date": "2026-03-02", "avg_value": 42.0, "max_value": 70.0},
                        {"date": "2026-03-03", "avg_value": 50.0, "max_value": 88.0},
                    ],
                }
            ],
            "resource_fluctuations": [
                {
                    "account_display_name": "Connect Prod",
                    "resource_id": "i-123456",
                    "resource_name": "web-1",
                    "metric_name": "cpu_utilization",
                    "sample_count": 20,
                    "days_with_samples": 10,
                    "avg_value": 50.2,
                    "min_value": 20.0,
                    "max_value": 90.0,
                    "daily_avg_range": 22.1,
                }
            ],
            "resource_daily_series": [
                {
                    "account_display_name": "Connect Prod",
                    "resource_id": "i-123456",
                    "resource_name": "web-1",
                    "metric_name": "cpu_utilization",
                    "daily_avg_range": 22.1,
                    "points": [
                        {"date": "2026-03-01", "avg_value": 41.0, "max_value": 66.0},
                        {"date": "2026-03-02", "avg_value": 52.0, "max_value": 78.0},
                        {"date": "2026-03-03", "avg_value": 63.0, "max_value": 90.0},
                    ],
                }
            ],
            "stuck_summary": {
                "threshold_days": stuck_days_threshold,
                "guardduty_active": 2,
                "cloudwatch_active": 1,
                "guardduty_stuck": 1,
                "cloudwatch_stuck": 1,
                "items": [
                    {
                        "check_name": "guardduty",
                        "account_display_name": "Connect Prod",
                        "severity": "HIGH",
                        "title": "Privilege escalation",
                        "age_days": 9,
                        "last_seen_at": "2026-03-26T01:00:00+00:00",
                    }
                ],
            },
            "cost_summary": {
                "impacted_accounts": 1,
                "accounts": [
                    {
                        "account_display_name": "Connect Prod",
                        "anomalies_today_peak": 2.0,
                        "anomalies_total_peak": 4.0,
                    }
                ],
            },
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

    workload_resp = client.get(
        "/api/v1/metrics/workload-monthly-report?customer_id=cust-1&year=2026&month=3"
    )
    assert workload_resp.status_code == 200
    workload_body = workload_resp.json()
    assert workload_body["customer_id"] == "cust-1"
    assert "metric_fluctuations" in workload_body
    assert "coverage" not in workload_body
    assert "daily_runs" not in workload_body

    workload_html_resp = client.get(
        "/api/v1/metrics/workload-monthly-report/html?customer_id=cust-1&year=2026&month=3"
    )
    assert workload_html_resp.status_code == 200
    assert "text/html" in workload_html_resp.headers.get("content-type", "")
    assert "Daily Trend Charts" in workload_html_resp.text
    assert "Resource Trend Charts (by Instance)" in workload_html_resp.text
    assert "i-123456" in workload_html_resp.text
    assert "<svg" in workload_html_resp.text
    assert "Top Missing Days" not in workload_html_resp.text
    assert "Total runs:" not in workload_html_resp.text

    workload_csv_resp = client.get(
        "/api/v1/metrics/workload-monthly-report/csv?customer_id=cust-1&year=2026&month=3"
    )
    assert workload_csv_resp.status_code == 200
    assert "text/csv" in workload_csv_resp.headers.get("content-type", "")
    assert "metric_fluctuations" in workload_csv_resp.text
    assert "daily_runs" not in workload_csv_resp.text
    assert "coverage,total_runs" not in workload_csv_resp.text

    dashboard_resp = client.get("/api/v1/dashboard/summary?customer_id=cust-1")
    assert dashboard_resp.status_code == 200
    dashboard_body = dashboard_resp.json()
    assert dashboard_body["customer_id"] == "cust-1"
    assert "runs" in dashboard_body
    assert "results" in dashboard_body
    assert "findings" in dashboard_body
    assert "metrics" in dashboard_body
    assert "top_checks" in dashboard_body
