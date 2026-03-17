from src.checks.generic.guardduty import GuardDutyChecker


def test_count_issues_ignores_low_severity_details():
    checker = GuardDutyChecker(region="ap-southeast-3")

    result = {
        "status": "success",
        "findings": 3,
        "details": [
            {"severity": "LOW"},
            {"severity": "LOW"},
            {"severity": "MEDIUM"},
        ],
    }

    assert checker.count_issues(result) == 1
