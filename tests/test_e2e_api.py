"""End-to-end backend tests against real PostgreSQL and AWS.

Run: python -m pytest tests/test_e2e_api.py -v -s
Requires: PostgreSQL running, AWS SSO credentials active
"""

import os
import pytest
from fastapi.testclient import TestClient

# Ensure we hit the real PostgreSQL
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://monitor:monitor@localhost:5432/monitoring",
)

from src.app.api.main import app  # noqa: E402

client = TestClient(app)

# Will be populated during tests
_customer_id = None
_account_id = None
_check_run_id = None


class TestHealth:
    def test_health(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestCustomerCRUD:
    def test_create_customer(self):
        global _customer_id
        r = client.post("/api/v1/customers", json={
            "name": "e2e-test-customer",
            "display_name": "E2E Test Customer",
            "checks": ["cost", "guardduty", "cloudwatch", "notifications"],
            "slack_enabled": False,
        })
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["name"] == "e2e-test-customer"
        assert data["checks"] == ["cost", "guardduty", "cloudwatch", "notifications"]
        assert len(data["id"]) == 36
        _customer_id = data["id"]

    def test_get_customer(self):
        r = client.get(f"/api/v1/customers/{_customer_id}")
        assert r.status_code == 200
        assert r.json()["name"] == "e2e-test-customer"

    def test_list_customers(self):
        r = client.get("/api/v1/customers")
        assert r.status_code == 200
        names = [c["name"] for c in r.json()["customers"]]
        assert "e2e-test-customer" in names

    def test_update_customer(self):
        r = client.patch(f"/api/v1/customers/{_customer_id}", json={
            "display_name": "E2E Updated",
            "checks": ["cost", "guardduty"],
        })
        assert r.status_code == 200
        assert r.json()["display_name"] == "E2E Updated"
        assert r.json()["checks"] == ["cost", "guardduty"]

    def test_duplicate_name_rejected(self):
        r = client.post("/api/v1/customers", json={
            "name": "e2e-test-customer",
            "display_name": "Duplicate",
        })
        assert r.status_code == 409

    def test_not_found(self):
        r = client.get("/api/v1/customers/nonexistent-id")
        assert r.status_code == 404


class TestAccounts:
    def test_add_account(self):
        global _account_id
        r = client.post(f"/api/v1/customers/{_customer_id}/accounts", json={
            "profile_name": "connect-prod",
            "display_name": "Connect Production",
        })
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["profile_name"] == "connect-prod"
        _account_id = data["id"]

    def test_account_appears_in_customer(self):
        r = client.get(f"/api/v1/customers/{_customer_id}")
        assert r.status_code == 200
        accounts = r.json()["accounts"]
        assert len(accounts) >= 1
        assert any(a["profile_name"] == "connect-prod" for a in accounts)

    def test_update_account(self):
        r = client.patch(f"/api/v1/customers/accounts/{_account_id}", json={
            "display_name": "Connect Prod (Updated)",
        })
        assert r.status_code == 200
        assert r.json()["display_name"] == "Connect Prod (Updated)"


class TestProfiles:
    def test_detect_profiles(self):
        r = client.get("/api/v1/profiles/detect")
        assert r.status_code == 200
        data = r.json()
        assert "all_profiles" in data
        assert "mapped_profiles" in data
        assert "unmapped_profiles" in data
        assert isinstance(data["all_profiles"], list)
        # connect-prod should be mapped now
        assert "connect-prod" in data["mapped_profiles"]


class TestCheckExecution:
    """Tests that hit real AWS — requires active SSO session."""

    def test_single_check_guardduty(self):
        global _check_run_id
        r = client.post("/api/v1/checks/execute", json={
            "customer_id": _customer_id,
            "mode": "single",
            "check_name": "guardduty",
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert "check_run_id" in data
        assert "results" in data
        assert "consolidated_output" in data
        assert len(data["results"]) >= 1
        # consolidated_output should have per-account output for single mode
        assert "connect-prod" in data["consolidated_output"].lower() or "Connect" in data["consolidated_output"]
        _check_run_id = data["check_run_id"]

        # Check result structure
        result = data["results"][0]
        assert result["status"] in ("OK", "WARN", "ERROR", "ALARM", "NO_DATA")
        assert result["check_name"] == "guardduty"
        assert "account" in result
        print(f"\n  GuardDuty result: {result['status']} - {result['summary']}")

    def test_single_check_cost(self):
        r = client.post("/api/v1/checks/execute", json={
            "customer_id": _customer_id,
            "mode": "single",
            "check_name": "cost",
        })
        assert r.status_code == 200, r.text
        data = r.json()
        result = data["results"][0]
        assert result["check_name"] == "cost"
        print(f"\n  Cost result: {result['status']} - {result['summary']}")

    def test_all_mode_consolidated_report(self):
        # First restore checks to the full set
        client.patch(f"/api/v1/customers/{_customer_id}", json={
            "checks": ["cost", "guardduty", "cloudwatch", "notifications"],
        })

        r = client.post("/api/v1/checks/execute", json={
            "customer_id": _customer_id,
            "mode": "all",
        })
        assert r.status_code == 200, r.text
        data = r.json()

        # Save results for each check
        check_names = {item["check_name"] for item in data["results"]}
        assert "cost" in check_names
        assert "guardduty" in check_names

        # consolidated_output should be a full report
        report = data["consolidated_output"]
        assert "DAILY MONITORING REPORT" in report
        assert "EXECUTIVE SUMMARY" in report
        assert "ASSESSMENT RESULTS" in report
        assert "ACCOUNT COVERAGE" in report
        print(f"\n  All-mode report length: {len(report)} chars")
        print(f"  First 200 chars:\n  {report[:200]}")

    def test_invalid_mode(self):
        r = client.post("/api/v1/checks/execute", json={
            "customer_id": _customer_id,
            "mode": "invalid",
        })
        assert r.status_code == 422  # pydantic validation

    def test_single_without_check_name(self):
        r = client.post("/api/v1/checks/execute", json={
            "customer_id": _customer_id,
            "mode": "single",
        })
        assert r.status_code == 400

    def test_available_checks(self):
        r = client.get("/api/v1/checks/available")
        assert r.status_code == 200
        names = [c["name"] for c in r.json()["checks"]]
        assert "cost" in names
        assert "guardduty" in names
        assert "daily-arbel" in names


class TestHistory:
    def test_list_history(self):
        r = client.get("/api/v1/history", params={
            "customer_id": _customer_id,
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert "total" in data
        assert "items" in data
        assert data["total"] >= 1
        # Should have the runs we created
        modes = {item["check_mode"] for item in data["items"]}
        assert "single" in modes or "all" in modes

    def test_history_filter_by_mode(self):
        r = client.get("/api/v1/history", params={
            "customer_id": _customer_id,
            "check_mode": "single",
        })
        assert r.status_code == 200
        for item in r.json()["items"]:
            assert item["check_mode"] == "single"

    def test_check_run_detail(self):
        r = client.get(f"/api/v1/history/{_check_run_id}")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["check_run_id"] == _check_run_id
        assert "customer" in data
        assert "results" in data
        assert len(data["results"]) >= 1
        # Each result should have full detail
        result = data["results"][0]
        assert "account" in result
        assert "status" in result
        assert "output" in result

    def test_check_run_not_found(self):
        r = client.get("/api/v1/history/nonexistent-id")
        assert r.status_code == 404


class TestCleanup:
    """Clean up test data."""

    def test_delete_customer(self):
        r = client.delete(f"/api/v1/customers/{_customer_id}")
        assert r.status_code == 204

    def test_customer_gone(self):
        r = client.get(f"/api/v1/customers/{_customer_id}")
        assert r.status_code == 404

    def test_history_empty_after_cascade(self):
        r = client.get("/api/v1/history", params={
            "customer_id": _customer_id,
        })
        assert r.status_code == 200
        assert r.json()["total"] == 0
