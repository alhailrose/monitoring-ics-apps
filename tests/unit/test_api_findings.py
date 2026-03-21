from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi.testclient import TestClient


class _FakeCheckRepository:
    def __init__(self, findings=None, total=0):
        self.findings = findings or []
        self.total = total
        self.calls = []

    def list_findings(
        self,
        customer_id,
        check_name=None,
        severity=None,
        account_id=None,
        limit=50,
        offset=0,
    ):
        self.calls.append(
            {
                "customer_id": customer_id,
                "check_name": check_name,
                "severity": severity,
                "account_id": account_id,
                "limit": limit,
                "offset": offset,
            }
        )
        return self.findings, self.total


def _make_finding():
    account = SimpleNamespace(
        id="acc-1", profile_name="connect-prod", display_name="Connect Prod"
    )
    return SimpleNamespace(
        id="fe-1",
        check_run_id="run-1",
        account=account,
        check_name="guardduty",
        finding_key="gd:1",
        severity="HIGH",
        title="Privilege escalation",
        description="Suspicious iam activity",
        created_at=datetime(2026, 3, 19, 10, 0, 0, tzinfo=timezone.utc),
    )


def test_findings_endpoint_returns_contract_shape():
    import backend.interfaces.api.dependencies as deps
    from backend.interfaces.api.main import create_app

    repo = _FakeCheckRepository(findings=[_make_finding()], total=1)

    app = create_app()
    app.dependency_overrides[deps.get_check_repository] = lambda: repo
    client = TestClient(app)

    response = client.get("/api/v1/findings?customer_id=cust-1")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["check_name"] == "guardduty"
    assert item["severity"] == "HIGH"
    assert item["account"]["profile_name"] == "connect-prod"


def test_findings_endpoint_forwards_filters_to_repository():
    import backend.interfaces.api.dependencies as deps
    from backend.interfaces.api.main import create_app

    repo = _FakeCheckRepository(findings=[], total=0)

    app = create_app()
    app.dependency_overrides[deps.get_check_repository] = lambda: repo
    client = TestClient(app)

    response = client.get(
        "/api/v1/findings?customer_id=cust-1&check_name=cloudwatch&severity=ALARM&account_id=acc-9&limit=25&offset=10"
    )

    assert response.status_code == 200
    assert len(repo.calls) == 1
    assert repo.calls[0] == {
        "customer_id": "cust-1",
        "check_name": "cloudwatch",
        "severity": "ALARM",
        "account_id": "acc-9",
        "limit": 25,
        "offset": 10,
    }
