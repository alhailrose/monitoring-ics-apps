from src.checks.generic.cost_anomalies import CostAnomalyChecker


def test_cost_anomaly_report_shows_latest_and_previous_day_context():
    checker = CostAnomalyChecker()

    results = {
        "status": "success",
        "profile": "acct-a",
        "account_id": "123456789012",
        "monitors": [{"MonitorName": "Main", "MonitorType": "DIMENSIONAL"}],
        "anomalies": [
            {
                "MonitorName": "Main",
                "AnomalyId": "a-today",
                "AnomalyStartDate": "2026-02-19",
                "AnomalyEndDate": "2026-02-19",
                "Impact": {
                    "TotalImpact": "55.0",
                    "TotalActualSpend": "155.0",
                    "TotalExpectedSpend": "100.0",
                    "TotalImpactPercentage": "55.0",
                },
            },
            {
                "MonitorName": "Main",
                "AnomalyId": "a-yesterday",
                "AnomalyStartDate": "2026-02-18",
                "AnomalyEndDate": "2026-02-18",
                "Impact": {
                    "TotalImpact": "12.0",
                    "TotalActualSpend": "112.0",
                    "TotalExpectedSpend": "100.0",
                    "TotalImpactPercentage": "12.0",
                },
            },
        ],
        "total_monitors": 1,
        "total_anomalies": 2,
        "today_anomaly_count": 1,
        "yesterday_anomaly_count": 1,
    }

    report = checker.format_report(results)

    assert "Latest anomaly snapshot" in report
    assert "Previous-day context" in report
    assert "Today anomalies: 1" in report
    assert "Yesterday anomalies: 1" in report
