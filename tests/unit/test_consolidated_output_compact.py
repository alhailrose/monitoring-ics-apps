from backend.checks.generic.notifications import NotificationChecker
from backend.checks.generic.cloudwatch_alarms import CloudWatchAlarmChecker


def test_notifications_render_section_shows_recent_notifications_detail():
    checker = NotificationChecker()
    all_results = {
        "acct-a": {
            "status": "success",
            "recent_count": 2,
            "total_managed": 7,
            "recent_events": [
                {
                    "creationTime": "2026-03-17T01:00:00Z",
                    "notificationEvent": {
                        "sourceEventMetadata": {"eventType": "AWS_HEALTH"},
                        "messageComponents": {"headline": "Maintenance"},
                    },
                }
            ],
            "all_events": [
                {
                    "creationTime": "2026-03-17T01:00:00Z",
                    "notificationEvent": {
                        "sourceEventMetadata": {"eventType": "AWS_HEALTH"},
                        "messageComponents": {"headline": "Maintenance"},
                    },
                }
            ],
        }
    }

    lines = checker.render_section(all_results, errors=[])

    assert any("last 12h" in line for line in lines)
    assert any("Recent notifications by account" in line for line in lines)
    assert any("acct-a" in line for line in lines)
    assert any("AWS_HEALTH" in line for line in lines)


def test_cloudwatch_render_section_omits_reason_in_consolidated_mode():
    checker = CloudWatchAlarmChecker()
    all_results = {
        "acct-a": {
            "status": "success",
            "account_id": "111111111111",
            "count": 1,
            "details": [
                {
                    "name": "HighCPU",
                    "reason": "Threshold Crossed: CPU > 80%",
                    "updated": "2026-03-17 09:00 WIB",
                }
            ],
        }
    }

    lines = checker.render_section(all_results, errors=[])

    assert any("Active Alarms" in line for line in lines)
    assert not any("Reason:" in line for line in lines)
