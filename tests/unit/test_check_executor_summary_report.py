from types import SimpleNamespace

from backend.domain.services.check_executor import _build_summary_report


class _FakeChecker:
    def __init__(self, key: str):
        self.key = key
        self.issue_label = "issues"

    def count_issues(self, result):
        if self.key == "notifications":
            return int(result.get("recent_count", 0) or 0)
        if self.key == "cloudwatch":
            return int(result.get("count", 0) or 0)
        if self.key == "guardduty":
            return int(result.get("findings", 0) or 0)
        return 0


def test_summary_report_includes_short_names_for_alarm_finding_notification():
    profiles = ["ksni-a"]
    checks = ["cloudwatch", "guardduty", "notifications"]
    checkers = {
        "cloudwatch": _FakeChecker("cloudwatch"),
        "guardduty": _FakeChecker("guardduty"),
        "notifications": _FakeChecker("notifications"),
    }
    all_results = {
        "ksni-a": {
            "cloudwatch": {
                "status": "success",
                "count": 1,
                "details": [{"name": "HCPortal DB Free Memory"}],
            },
            "guardduty": {
                "status": "success",
                "findings": 1,
                "details": [{"title": "Privilege escalation detected"}],
            },
            "notifications": {
                "status": "success",
                "recent_count": 1,
                "recent_events": [
                    {
                        "notificationEvent": {
                            "sourceEventMetadata": {"eventType": "AWS_HEALTH"},
                            "messageComponents": {"headline": "Planned maintenance"},
                        }
                    }
                ],
            },
        }
    }

    accounts = [
        SimpleNamespace(
            profile_name="ksni-a", display_name="KSNI A", account_id="123456789012"
        )
    ]

    out = _build_summary_report(
        profiles=profiles,
        all_results=all_results,
        checks=checks,
        checkers=checkers,
        check_errors=[],
        clean_accounts=[],
        region="ap-southeast-3",
        group_name="KSNI",
        accounts=accounts,
    )

    assert "Ringkasan Check Lain" in out
    assert "| contoh:" not in out
    assert "- Notifikasi (12 jam): 1 notifikasi baru" in out
    assert "  • Planned maintenance" in out
    assert "- GuardDuty Finding: 1 finding pada KSNI A (123456789012)" in out
    assert "  • Privilege escalation detected" in out
    assert "- Alarm CloudWatch: 1 alarm pada KSNI A (123456789012)" in out
    assert "  • HCPortal DB Free Memory" in out
