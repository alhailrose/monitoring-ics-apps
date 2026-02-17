from checks.daily_arbel import ACCOUNT_CONFIG, DailyArbelChecker
from datetime import datetime, timedelta, timezone


class _CloudWatchStub:
    def __init__(self, threshold=None):
        self.threshold = threshold

    def describe_alarms(self, AlarmNames):
        if self.threshold is None:
            return {"MetricAlarms": []}
        return {
            "MetricAlarms": [{"AlarmName": AlarmNames[0], "Threshold": self.threshold}]
        }


def test_resolve_role_thresholds_uses_alarm_threshold_for_freeable_memory():
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=3)
    cfg = ACCOUNT_CONFIG["dermies-max"]
    base = dict(cfg["thresholds"])

    thresholds = checker._resolve_role_thresholds(
        _CloudWatchStub(threshold=8 * 1024**3),
        "dermies-max",
        "writer",
        base,
    )

    assert thresholds["FreeableMemory"] == 8 * 1024**3


def test_resolve_role_thresholds_falls_back_to_base_threshold_if_alarm_missing():
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=3)
    cfg = ACCOUNT_CONFIG["dermies-max"]
    base = dict(cfg["thresholds"])

    thresholds = checker._resolve_role_thresholds(
        _CloudWatchStub(threshold=None),
        "dermies-max",
        "writer",
        base,
    )

    assert thresholds["FreeableMemory"] == base["FreeableMemory"]


def test_extract_alarm_periods_parses_closed_and_ongoing_ranges():
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=12)
    now_utc = datetime(2026, 2, 16, 8, 0, tzinfo=timezone.utc)

    history = [
        {
            "HistorySummary": "Alarm updated from ALARM to OK",
            "Timestamp": datetime(2026, 2, 16, 2, 45, tzinfo=timezone.utc),
        },
        {
            "HistorySummary": "Alarm updated from OK to ALARM",
            "Timestamp": datetime(2026, 2, 16, 2, 32, tzinfo=timezone.utc),
        },
        {
            "HistorySummary": "Alarm updated from OK to ALARM",
            "Timestamp": datetime(2026, 2, 16, 7, 35, tzinfo=timezone.utc),
        },
    ]

    window_start = now_utc - timedelta(hours=12)
    periods = checker._extract_alarm_periods(
        history,
        now_utc,
        window_start,
        current_state="ALARM",
    )

    assert len(periods) == 2
    assert periods[0][3] == 13
    assert periods[1][3] == 25


def test_extract_alarm_periods_clips_period_start_to_window_boundary():
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=1)
    now_utc = datetime(2026, 2, 16, 8, 0, tzinfo=timezone.utc)
    window_start = now_utc - timedelta(hours=1)

    history = [
        {
            "HistorySummary": "Alarm updated from ALARM to OK",
            "Timestamp": datetime(2026, 2, 16, 7, 20, tzinfo=timezone.utc),
        }
    ]

    periods = checker._extract_alarm_periods(
        history,
        now_utc,
        window_start,
        current_state="OK",
    )

    assert len(periods) == 1
    assert periods[0][1] == "14:00"
    assert periods[0][2] == "14:20"
    assert periods[0][3] == 20


def test_evaluate_metric_uses_alarm_history_when_metric_breach_missing():
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=12)

    status, msg = checker._evaluate_metric(
        "FreeableMemory",
        {
            "last": 10.2 * 1024**3,
            "values": [10.2 * 1024**3],
            "timestamps": [datetime(2026, 2, 16, 8, 0, tzinfo=timezone.utc)],
            "alarm_periods": [(0.0, "12:32", "12:45", 13)],
        },
        {"FreeableMemory": 10 * 1024**3},
        "dermies-max",
    )

    assert status == "past-warn"
    assert "sekarang normal" in msg
    assert "ALARM pukul 12:32-12:45 WIB (13 menit)" in msg
