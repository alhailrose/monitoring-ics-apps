import checks.daily_budget as daily_budget
from checks.daily_budget import DailyBudgetChecker
from monitoring_hub.reports import build_whatsapp_budget


class _BudgetsClientStub:
    def __init__(self, budgets, notifications_by_name):
        self._budgets = budgets
        self._notifications = notifications_by_name

    def describe_budgets(self, AccountId, NextToken=None):
        return {"Budgets": self._budgets}

    def describe_notifications_for_budget(self, AccountId, BudgetName):
        return {"Notifications": self._notifications.get(BudgetName, [])}


class _SessionStub:
    def __init__(self, client):
        self._client = client

    def client(self, service_name, region_name=None):
        assert service_name == "budgets"
        return self._client


def test_daily_budget_checker_marks_threshold_exceeded(monkeypatch):
    budget = {
        "BudgetName": "PublicWeb-Daily-Budget-Cost",
        "TimeUnit": "DAILY",
        "BudgetLimit": {"Amount": "67", "Unit": "USD"},
        "CalculatedSpend": {"ActualSpend": {"Amount": "64.259", "Unit": "USD"}},
    }
    notifications = {
        "PublicWeb-Daily-Budget-Cost": [
            {
                "NotificationType": "ACTUAL",
                "ComparisonOperator": "GREATER_THAN",
                "Threshold": 95,
            }
        ]
    }
    client = _BudgetsClientStub([budget], notifications)

    monkeypatch.setattr(
        daily_budget.boto3,
        "Session",
        lambda profile_name, region_name=None: _SessionStub(client),
        raising=False,
    )

    checker = DailyBudgetChecker(region="ap-southeast-3")
    result = checker.check("public-web", "211125667194")

    assert result["status"] == "ATTENTION REQUIRED"
    assert result["threshold_exceeded_count"] == 1
    assert result["over_budget_count"] == 0


def test_daily_budget_checker_marks_over_budget(monkeypatch):
    budget = {
        "BudgetName": "Budget-RDS-Only-CIS-Erha",
        "TimeUnit": "DAILY",
        "BudgetLimit": {"Amount": "100", "Unit": "USD"},
        "CalculatedSpend": {"ActualSpend": {"Amount": "101.055", "Unit": "USD"}},
    }
    notifications = {
        "Budget-RDS-Only-CIS-Erha": [
            {
                "NotificationType": "ACTUAL",
                "ComparisonOperator": "GREATER_THAN",
                "Threshold": 100,
            }
        ]
    }
    client = _BudgetsClientStub([budget], notifications)

    monkeypatch.setattr(
        daily_budget.boto3,
        "Session",
        lambda profile_name, region_name=None: _SessionStub(client),
        raising=False,
    )

    checker = DailyBudgetChecker(region="ap-southeast-3")
    result = checker.check("cis-erha", "451916275465")

    assert result["status"] == "ATTENTION REQUIRED"
    assert result["over_budget_count"] == 1


def test_build_whatsapp_budget_formats_grouped_output():
    all_results = {
        "connect-prod": {
            "daily-budget": {
                "status": "ATTENTION REQUIRED",
                "account_id": "620463044477",
                "account_name": "Connect Prod (Non Cis)",
                "items": [
                    {
                        "budget_name": "Budget-Log-Only-CONNECT-Prod",
                        "actual": 9.11,
                        "limit": 7.0,
                        "percent": 130.19,
                        "over_amount": 2.11,
                        "threshold_hits": [95.0],
                        "is_over_budget": True,
                    }
                ],
            }
        },
        "cis-erha": {
            "daily-budget": {
                "status": "ATTENTION REQUIRED",
                "account_id": "451916275465",
                "account_name": "CIS Erha",
                "items": [
                    {
                        "budget_name": "Budget-RDS-Only-CIS-Erha",
                        "actual": 109.33,
                        "limit": 100.0,
                        "percent": 109.33,
                        "over_amount": 9.33,
                        "threshold_hits": [100.0],
                        "is_over_budget": True,
                    }
                ],
            }
        },
    }

    msg = build_whatsapp_budget(all_results)

    assert "1) Account 620463044477 - Connect Prod (Non Cis)" in msg
    assert "Budget-Log-Only-CONNECT-Prod: $9.11 / $7.00 (130.19%)" in msg
    assert "2) Account 451916275465 - CIS Erha" in msg
