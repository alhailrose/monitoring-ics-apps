from src.app.services.finding_events_mapper import map_check_findings


def test_map_guardduty_details_to_finding_events():
    raw = {
        "status": "success",
        "details": [
            {
                "type": "Recon:EC2/PortProbeUnprotectedPort",
                "severity": "HIGH",
                "title": "Port probe detected",
                "updated": "2026-03-19 13:00 WIB",
            }
        ],
    }

    events = map_check_findings(
        check_name="guardduty",
        account_id="acct-1",
        raw_result=raw,
    )

    assert len(events) == 1
    event = events[0]
    assert event["check_name"] == "guardduty"
    assert event["account_id"] == "acct-1"
    assert event["severity"] == "HIGH"
    assert event["title"] == "Port probe detected"
    assert event["finding_key"] == "Recon:EC2/PortProbeUnprotectedPort"


def test_map_cloudwatch_details_to_finding_events():
    raw = {
        "status": "success",
        "details": [
            {
                "name": "rds-cpu-alarm",
                "reason": "Threshold Crossed",
                "updated": "2026-03-19 13:01 WIB",
            }
        ],
    }

    events = map_check_findings(
        check_name="cloudwatch",
        account_id="acct-2",
        raw_result=raw,
    )

    assert len(events) == 1
    event = events[0]
    assert event["check_name"] == "cloudwatch"
    assert event["severity"] == "ALARM"
    assert event["title"] == "rds-cpu-alarm"
    assert event["finding_key"] == "rds-cpu-alarm"
    assert event["description"] == "Threshold Crossed"


def test_map_notifications_recent_events_to_finding_events():
    raw = {
        "status": "success",
        "recent_events": [
            {
                "creationTime": "2026-03-19T05:00:00Z",
                "notificationEvent": {
                    "sourceEventMetadata": {"eventType": "AWS_RISK"},
                    "messageComponents": {"headline": "Security update available"},
                },
            }
        ],
    }

    events = map_check_findings(
        check_name="notifications",
        account_id="acct-3",
        raw_result=raw,
    )

    assert len(events) == 1
    event = events[0]
    assert event["check_name"] == "notifications"
    assert event["severity"] == "INFO"
    assert event["title"] == "Security update available"
    assert event["finding_key"] == "AWS_RISK"


def test_map_check_findings_returns_empty_for_unsupported_check():
    events = map_check_findings(
        check_name="ec2",
        account_id="acct-4",
        raw_result={"status": "success", "details": [{"foo": "bar"}]},
    )

    assert events == []


def test_map_check_findings_returns_empty_for_error_status():
    events = map_check_findings(
        check_name="guardduty",
        account_id="acct-5",
        raw_result={"status": "error", "details": [{"type": "x"}]},
    )

    assert events == []


def test_map_notifications_handles_malformed_nested_payloads_safely():
    raw = {
        "status": "success",
        "recent_events": [
            {
                "creationTime": "2026-03-19T05:00:00Z",
                "notificationEvent": "invalid",
            },
            {
                "creationTime": "2026-03-19T05:10:00Z",
                "notificationEvent": {
                    "sourceEventMetadata": "invalid",
                    "messageComponents": ["invalid"],
                },
            },
        ],
    }

    events = map_check_findings(
        check_name="notifications",
        account_id="acct-6",
        raw_result=raw,
    )

    assert len(events) == 2
    assert events[0]["finding_key"] == "notification"
    assert events[0]["title"] == "notification"
    assert events[1]["finding_key"] == "notification"
    assert events[1]["title"] == "notification"
