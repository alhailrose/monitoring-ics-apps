from backend.checks.generic.cloudwatch_alarms import CloudWatchAlarmChecker


def test_format_report_shows_alarm_count_and_names_when_active():
    checker = CloudWatchAlarmChecker(region="ap-southeast-3")
    result = {
        "status": "success",
        "count": 2,
        "details": [
            {
                "name": "ucoal-chain-prod-openvpn-cpu-above-70",
                "reason": "Threshold Crossed",
                "updated": "2026-03-17 10:11 WIB",
            },
            {
                "name": "ucoal-chain-prod-openvpn-disk-above-70",
                "reason": "Threshold Crossed",
                "updated": "2026-03-17 10:12 WIB",
            },
        ],
    }

    report = checker.format_report(result)

    assert "Status: 2 alarm(s) in ALARM state" in report
    assert "ucoal-chain-prod-openvpn-cpu-above-70" in report
    assert "ucoal-chain-prod-openvpn-disk-above-70" in report
