from backend.checks.aryanoble.daily_arbel import ACCOUNT_CONFIG, DailyArbelChecker
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


class _CloudWatchMetricAlarmsStub:
    def __init__(self, thresholds):
        self.thresholds = thresholds

    def describe_alarms_for_metric(self, Namespace, MetricName, Dimensions):
        _ = Namespace, MetricName, Dimensions
        return {"MetricAlarms": [{"Threshold": value} for value in self.thresholds]}


class _CloudWatchRoleAwareStub:
    def describe_alarms_for_metric(self, Namespace, MetricName, Dimensions):
        _ = Namespace, MetricName
        dimensions_set = {(d.get("Name"), d.get("Value")) for d in Dimensions}
        if dimensions_set == {
            ("DBClusterIdentifier", "cis-prod-rds"),
            ("Role", "WRITER"),
        }:
            return {"MetricAlarms": [{"Threshold": 24.0}]}
        return {"MetricAlarms": []}


class _CloudWatchRegionAlarmStub:
    def __init__(self, region_name, state_by_alarm=None, history_by_alarm=None):
        self.meta = type("Meta", (), {"region_name": region_name})()
        self._state_by_alarm = state_by_alarm or {}
        self._history_by_alarm = history_by_alarm or {}

    def describe_alarms(self, AlarmNames):
        name = AlarmNames[0]
        state = self._state_by_alarm.get(name)
        if state is None:
            return {"MetricAlarms": []}
        return {"MetricAlarms": [{"AlarmName": name, "StateValue": state}]}

    def describe_alarm_history(self, AlarmName, **_kwargs):
        return {"AlarmHistoryItems": self._history_by_alarm.get(AlarmName, [])}


class _SessionRegionStub:
    def __init__(self, clients):
        self.clients = clients

    def client(self, service_name, region_name=None):
        _ = service_name
        return self.clients[region_name]


def test_check_ec2_alarms_falls_back_to_configured_alarm_regions():
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=12)
    alarm_name = "aryanoble-prod-Window2019Base-webserver Disk D < 10%"

    primary = _CloudWatchRegionAlarmStub(
        "ap-southeast-3",
        state_by_alarm={},
        history_by_alarm={},
    )
    fallback = _CloudWatchRegionAlarmStub(
        "ap-southeast-1",
        state_by_alarm={alarm_name: "ALARM"},
        history_by_alarm={alarm_name: []},
    )
    session = _SessionRegionStub(
        {
            "ap-southeast-3": primary,
            "ap-southeast-1": fallback,
        }
    )

    alarms = checker._check_ec2_alarms(
        primary,
        "HRIS",
        "webserver",
        cfg={
            "alarm_thresholds": {"webserver": [alarm_name]},
            "alarm_regions": ["ap-southeast-1"],
        },
        session=session,
    )

    assert len(alarms) == 1
    assert alarms[0]["alarm_name"] == alarm_name
    assert alarms[0]["current_state"] == "ALARM"


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


def test_evaluate_metric_db_connections_detects_ten_datapoint_past_breach():
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=12)
    base = datetime(2026, 3, 20, 1, 0, tzinfo=timezone.utc)

    values = [100.0] * 10 + [40.0] * 2
    status, msg = checker._evaluate_metric(
        "DatabaseConnections",
        {
            "last": 40.0,
            "values": values,
            "timestamps": [base + timedelta(minutes=i) for i in range(len(values))],
        },
        {"DatabaseConnections": 80.0},
        "connect-prod",
    )

    assert status == "past-warn"
    assert "(10 menit)" in msg


def test_evaluate_metric_ec2_cpu_detects_five_datapoint_spike():
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=12)
    base = datetime(2026, 3, 20, 1, 0, tzinfo=timezone.utc)

    values = [90.0] * 5 + [40.0] * 2
    status, msg = checker._evaluate_metric(
        "CPUUtilization",
        {
            "last": 40.0,
            "avg": 55.0,
            "values": values,
            "timestamps": [base + timedelta(minutes=i) for i in range(len(values))],
        },
        {"CPUUtilization": 80.0},
        "sfa",
        service_type="ec2",
    )

    assert status == "past-warn"
    assert "(5 menit)" in msg


def test_evaluate_metric_rds_acu_reports_short_past_spike():
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=12)
    base = datetime(2026, 3, 20, 1, 0, tzinfo=timezone.utc)

    values = [30.0, 90.0, 90.0, 90.0, 90.0, 30.0]
    status, msg = checker._evaluate_metric(
        "ACUUtilization",
        {
            "last": 30.0,
            "avg": sum(values) / len(values),
            "values": values,
            "timestamps": [base + timedelta(minutes=i) for i in range(len(values))],
        },
        {"ACUUtilization": 75.0},
        "connect-prod",
        service_type="rds",
    )

    assert status == "past-warn"
    assert "sempat > 75%" in msg
    assert "(4 menit)" in msg


def test_evaluate_metric_rds_freeable_memory_reports_short_past_drop():
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=12)
    base = datetime(2026, 3, 20, 1, 0, tzinfo=timezone.utc)

    values = [12 * 1024**3, 8 * 1024**3, 8 * 1024**3, 8 * 1024**3, 12 * 1024**3]
    status, msg = checker._evaluate_metric(
        "FreeableMemory",
        {
            "last": 12 * 1024**3,
            "values": values,
            "timestamps": [base + timedelta(minutes=i) for i in range(len(values))],
        },
        {"FreeableMemory": 10 * 1024**3},
        "connect-prod",
        service_type="rds",
    )

    assert status == "past-warn"
    assert "sempat <" in msg
    assert "(3 menit)" in msg


def test_evaluate_metric_serverless_capacity_reports_four_minute_spike():
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=12)
    base = datetime(2026, 3, 20, 1, 0, tzinfo=timezone.utc)

    values = [10.0, 25.0, 25.0, 25.0, 25.0, 10.0]
    status, msg = checker._evaluate_metric(
        "ServerlessDatabaseCapacity",
        {
            "last": 10.0,
            "values": values,
            "timestamps": [base + timedelta(minutes=i) for i in range(len(values))],
        },
        {"ServerlessDatabaseCapacity": 24.0},
        "cis-erha",
        service_type="rds",
    )

    assert status == "past-warn"
    assert "sempat > 24 ACU" in msg
    assert "(4 menit)" in msg


def test_evaluate_metric_buffer_cache_ignores_one_minute_noise():
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=12)
    base = datetime(2026, 3, 20, 1, 0, tzinfo=timezone.utc)

    values = [99.0, 80.0, 99.0]
    status, msg = checker._evaluate_metric(
        "BufferCacheHitRatio",
        {
            "last": 99.0,
            "values": values,
            "timestamps": [base + timedelta(minutes=i) for i in range(len(values))],
        },
        {"BufferCacheHitRatio": 90.0},
        "cis-erha",
        service_type="rds",
    )

    assert status == "ok"
    assert "normal" in msg


def test_should_emphasize_alarm_message_for_10min_or_more():
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=12)

    assert checker._should_emphasize_alarm_message(
        {
            "status": "warn",
            "message": "CPU Utilization: 90% (di atas 75%) | ALARM pukul 12:00-12:15 WIB (15 menit)",
        }
    )


def test_format_rds_detail_bolds_long_alarm_message():
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=12)
    lines = []
    checker._format_rds_detail(
        {
            "instances": {
                "writer": {
                    "instance_id": "cis-prod-rds-instance",
                    "metrics": {
                        "CPUUtilization": {
                            "status": "warn",
                            "message": "CPU Utilization: 90% (di atas 75%) | ALARM pukul 12:00-12:15 WIB (15 menit)",
                        }
                    },
                }
            }
        },
        lines,
    )

    assert (
        "* *CPU Utilization: 90% (di atas 75%) | ALARM pukul 12:00-12:15 WIB (15 menit)*"
        in lines
    )


def test_count_issues_includes_extra_sections():
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=12)
    result = {
        "status": "ATTENTION REQUIRED",
        "instances": {
            "writer": {
                "metrics": {
                    "CPUUtilization": {
                        "status": "ok",
                        "message": "CPU Utilization: 50% (normal)",
                    }
                }
            }
        },
        "extra_sections": [
            {
                "section_name": "CIS ERHA EC2",
                "service_type": "ec2",
                "instances": {
                    "rabbitmq": {
                        "metrics": {
                            "CPUUtilization": {
                                "status": "warn",
                                "message": "CPU Utilization: 85% (di atas 75%) | ALARM pukul 10:00-10:20 WIB (20 menit)",
                            }
                        }
                    }
                },
            }
        ],
    }

    assert checker.count_issues(result) == 1


def test_format_report_renders_extra_ec2_section():
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=12)
    report = checker.format_report(
        {
            "status": "OK",
            "profile": "cis-erha",
            "account_id": "451916275465",
            "account_name": "CIS ERHA",
            "service_type": "rds",
            "instances": {},
            "extra_sections": [
                {
                    "section_name": "CIS ERHA EC2",
                    "service_type": "ec2",
                    "instances": {
                        "rabbitmq": {
                            "instance_id": "i-076e1d2c0c3478c21",
                            "instance_name": "aws-prod-rabbitmq",
                            "metrics": {
                                "CPUUtilization": {
                                    "status": "warn",
                                    "message": "CPU Utilization: 88% (di atas 80%) | ALARM pukul 10:00-10:20 WIB (20 menit)",
                                }
                            },
                            "disk_memory_alarms": [],
                        }
                    },
                }
            ],
        }
    )

    assert "CIS ERHA EC2 (EC2):" in report
    assert "Instances: aws-prod-rabbitmq (i-076e1d2c0c3478c21)" in report
    assert "aws-prod-rabbitmq pukul 10:00-10:20 WIB (20 menit)" in report


def test_format_ec2_summary_keeps_disk_memory_alarm_period_6_minutes():
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=12)
    lines = []

    checker._format_ec2_summary(
        {
            "instances": {
                "webserver": {
                    "instance_id": "i-053c5b7302686e05d",
                    "instance_name": "webserver",
                    "metrics": {},
                    "disk_memory_alarms": [
                        {
                            "alarm_name": "disk-c-low",
                            "current_state": "OK",
                            "periods": [(0.0, "07:00", "07:06", 6)],
                        }
                    ],
                }
            }
        },
        lines,
    )

    assert any("07:00-07:06 WIB (6 menit)" in line for line in lines)


def test_format_report_uses_result_window_hours_for_rds_header():
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=12)

    report = checker.format_report(
        {
            "status": "OK",
            "profile": "cis-erha",
            "account_id": "451916275465",
            "account_name": "CIS ERHA",
            "service_type": "rds",
            "window_hours": 3,
            "instances": {},
            "extra_sections": [],
        }
    )

    assert "monitoring 3 jam terakhir" in report


def test_format_report_uses_result_window_hours_for_ec2_header():
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=12)

    report = checker.format_report(
        {
            "status": "OK",
            "profile": "cis-erha",
            "account_id": "451916275465",
            "account_name": "CIS ERHA",
            "service_type": "ec2",
            "window_hours": 1,
            "instances": {},
            "extra_sections": [],
        }
    )

    assert "monitoring 1 jam terakhir" in report


def test_resolve_live_threshold_uses_min_for_above_metrics():
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=12)
    cw = _CloudWatchMetricAlarmsStub([85, 75, 80])

    threshold = checker._resolve_live_threshold(
        cw,
        "rds",
        "cis-prod-rds-instance",
        "CPUUtilization",
    )

    assert threshold == 75


def test_resolve_live_threshold_uses_max_for_below_metrics():
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=12)
    cw = _CloudWatchMetricAlarmsStub([400 * 1024**2, 800 * 1024**2])

    threshold = checker._resolve_live_threshold(
        cw,
        "rds",
        "erhabuddy-prod-mysql-db",
        "FreeableMemory",
    )

    assert threshold == 800 * 1024**2


def test_resolve_live_threshold_supports_cluster_role_dimensions():
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=12)

    threshold = checker._resolve_live_threshold(
        _CloudWatchRoleAwareStub(),
        "rds",
        "cis-prod-rds-instance",
        "ServerlessDatabaseCapacity",
        cluster_id="cis-prod-rds",
        role="writer",
    )

    assert threshold == 24.0


def test_collect_section_report_sets_ec2_instance_name_from_config(monkeypatch):
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=12)

    monkeypatch.setattr(
        checker,
        "_fetch_metrics",
        lambda *args, **kwargs: {
            "CPUUtilization": {
                "max": 65,
                "breach_count": 0,
                "alarm_periods": [],
            }
        },
    )
    monkeypatch.setattr(
        checker,
        "_resolve_role_thresholds",
        lambda *args, **kwargs: {"CPUUtilization": 80},
    )
    monkeypatch.setattr(
        checker, "_resolve_live_threshold", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(checker, "_check_ec2_alarms", lambda *args, **kwargs: [])

    class _SessionStub:
        def client(self, service_name, region_name=None):
            _ = service_name, region_name
            return object()

    reports, _ = checker._collect_section_report(
        _SessionStub(),
        object(),
        "cis-erha",
        {
            "service_type": "ec2",
            "instances": {"rabbitmq": "i-076e1d2c0c3478c21"},
            "instance_names": {"i-076e1d2c0c3478c21": "aws-prod-rabbitmq"},
            "metrics": ["CPUUtilization"],
            "thresholds": {"CPUUtilization": 80},
        },
    )

    assert reports["rabbitmq"]["instance_name"] == "aws-prod-rabbitmq"


def test_collect_section_report_ignores_ec2_cpu_spike_5_minutes_or_less(monkeypatch):
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=1)
    base = datetime(2026, 3, 20, 1, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(
        checker,
        "_fetch_metrics",
        lambda *args, **kwargs: {
            "CPUUtilization": {
                "last": 68.0,
                "avg": (65.0 + 72.0 + 68.0) / 3,
                "max": 72.0,
                "values": [65.0, 72.0, 68.0],
                "timestamps": [
                    base,
                    base + timedelta(minutes=1),
                    base + timedelta(minutes=2),
                ],
            }
        },
    )
    monkeypatch.setattr(
        checker,
        "_resolve_role_thresholds",
        lambda *args, **kwargs: {"CPUUtilization": 70.0},
    )
    monkeypatch.setattr(
        checker, "_resolve_live_threshold", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(checker, "_check_ec2_alarms", lambda *args, **kwargs: [])

    class _SessionStub:
        def client(self, service_name, region_name=None):
            _ = service_name, region_name
            return object()

    reports, any_warn = checker._collect_section_report(
        _SessionStub(),
        object(),
        "sfa",
        {
            "service_type": "ec2",
            "instances": {"vm-sfa": "i-0cb272299353b6831"},
            "instance_names": {"i-0cb272299353b6831": "vm-sfa"},
            "metrics": ["CPUUtilization"],
            "thresholds": {"CPUUtilization": 70.0},
        },
    )

    assert reports["vm-sfa"]["metrics"]["CPUUtilization"]["status"] == "ok"
    assert any_warn is False


def test_evaluate_metric_ec2_cpu_uses_average_not_latest_and_shows_longest_spike():
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=1)
    base = datetime(2026, 3, 20, 1, 0, tzinfo=timezone.utc)

    values = [60.0, 80.0, 80.0, 80.0, 80.0, 80.0, 80.0, 80.0]
    status, msg = checker._evaluate_metric(
        "CPUUtilization",
        {
            "last": 60.0,
            "avg": sum(values) / len(values),
            "values": values,
            "timestamps": [base + timedelta(minutes=i) for i in range(len(values))],
        },
        {"CPUUtilization": 70.0},
        "sfa",
        service_type="ec2",
    )

    assert status == "warn"
    assert "rata-rata" in msg
    assert "spike terlama 7 menit" in msg


def test_evaluate_metric_ec2_cpu_detects_5_minute_spike_with_low_average():
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=12)
    base = datetime(2026, 3, 20, 1, 0, tzinfo=timezone.utc)

    values = [40.0] * 20 + [80.0] * 6 + [40.0] * 20
    status, msg = checker._evaluate_metric(
        "CPUUtilization",
        {
            "last": 40.0,
            "avg": sum(values) / len(values),
            "values": values,
            "timestamps": [base + timedelta(minutes=i) for i in range(len(values))],
        },
        {"CPUUtilization": 70.0},
        "sfa",
        service_type="ec2",
    )

    assert status == "past-warn"
    assert "spike terlama 6 menit" in msg


def test_evaluate_metric_ec2_cpu_detects_sparse_5_minute_spike():
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=1)
    base = datetime(2026, 3, 20, 1, 0, tzinfo=timezone.utc)

    status, msg = checker._evaluate_metric(
        "CPUUtilization",
        {
            "last": 40.0,
            "avg": 65.0,
            "values": [40.0, 90.0, 90.0, 40.0],
            "timestamps": [
                base,
                base + timedelta(minutes=5),
                base + timedelta(minutes=10),
                base + timedelta(minutes=15),
            ],
        },
        {"CPUUtilization": 80.0},
        "HRIS",
        service_type="ec2",
    )

    assert status == "past-warn"
    assert "pukul" in msg


def test_collect_section_report_ec2_cpu_ignores_higher_live_alarm_threshold(
    monkeypatch,
):
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=12)
    base = datetime(2026, 3, 20, 1, 0, tzinfo=timezone.utc)

    values = [40.0] * 20 + [80.0] * 6 + [40.0] * 20
    monkeypatch.setattr(
        checker,
        "_fetch_metrics",
        lambda *args, **kwargs: {
            "CPUUtilization": {
                "last": 40.0,
                "avg": sum(values) / len(values),
                "max": max(values),
                "values": values,
                "timestamps": [base + timedelta(minutes=i) for i in range(len(values))],
            }
        },
    )
    monkeypatch.setattr(
        checker,
        "_resolve_role_thresholds",
        lambda *args, **kwargs: {"CPUUtilization": 70.0},
    )
    monkeypatch.setattr(
        checker,
        "_resolve_live_threshold",
        lambda *args, **kwargs: 90.0,
    )
    monkeypatch.setattr(checker, "_check_ec2_alarms", lambda *args, **kwargs: [])

    class _SessionStub:
        def client(self, service_name, region_name=None):
            _ = service_name, region_name
            return object()

    reports, any_warn = checker._collect_section_report(
        _SessionStub(),
        object(),
        "sfa",
        {
            "service_type": "ec2",
            "instances": {"vm-sfa": "i-0cb272299353b6831"},
            "instance_names": {"i-0cb272299353b6831": "vm-sfa"},
            "metrics": ["CPUUtilization"],
            "thresholds": {"CPUUtilization": 70.0},
        },
    )

    assert reports["vm-sfa"]["metrics"]["CPUUtilization"]["status"] == "past-warn"
    assert any_warn is True


def test_check_rds_scope_skips_extra_ec2_section(monkeypatch):
    checker = DailyArbelChecker(
        region="ap-southeast-3", window_hours=3, section_scope="rds"
    )
    calls = []

    monkeypatch.setattr(
        checker,
        "_resolve_account_config",
        lambda profile, account_id: {
            "account_name": "CIS ERHA",
            "cluster_id": "cis-prod-rds",
            "service_type": "rds",
            "instances": {"writer": "cis-prod-rds-instance"},
            "metrics": ["CPUUtilization"],
            "thresholds": {"CPUUtilization": 75},
            "extra_sections": [
                {
                    "section_name": "CIS ERHA EC2",
                    "service_type": "ec2",
                    "instances": {"rabbitmq": "i-076e1d2c0c3478c21"},
                    "metrics": ["CPUUtilization"],
                    "thresholds": {"CPUUtilization": 80},
                }
            ],
        },
    )
    monkeypatch.setattr(
        checker,
        "_collect_section_report",
        lambda session, cw, profile, cfg: (
            calls.append(cfg.get("service_type")) or {"writer": {"metrics": {}}},
            False,
        ),
    )

    class _SessionStub:
        def client(self, service_name, region_name=None):
            _ = service_name, region_name
            return object()

    monkeypatch.setattr(
        "backend.checks.aryanoble.daily_arbel.boto3.Session",
        lambda *args, **kwargs: _SessionStub(),
    )

    result = checker.check("cis-erha", "451916275465")

    assert calls == ["rds"]
    assert result.get("extra_sections") == []


def test_check_ec2_scope_skips_rds_section(monkeypatch):
    checker = DailyArbelChecker(
        region="ap-southeast-3", window_hours=3, section_scope="ec2"
    )
    calls = []

    monkeypatch.setattr(
        checker,
        "_resolve_account_config",
        lambda profile, account_id: {
            "account_name": "CIS ERHA",
            "cluster_id": "cis-prod-rds",
            "service_type": "rds",
            "instances": {"writer": "cis-prod-rds-instance"},
            "metrics": ["CPUUtilization"],
            "thresholds": {"CPUUtilization": 75},
            "extra_sections": [
                {
                    "section_name": "CIS ERHA EC2",
                    "service_type": "ec2",
                    "instances": {"rabbitmq": "i-076e1d2c0c3478c21"},
                    "instance_names": {"i-076e1d2c0c3478c21": "aws-prod-rabbitmq"},
                    "metrics": ["CPUUtilization"],
                    "thresholds": {"CPUUtilization": 80},
                }
            ],
        },
    )
    monkeypatch.setattr(
        checker,
        "_collect_section_report",
        lambda session, cw, profile, cfg: (
            calls.append(cfg.get("service_type")) or {"rabbitmq": {"metrics": {}}},
            False,
        ),
    )

    class _SessionStub:
        def client(self, service_name, region_name=None):
            _ = service_name, region_name
            return object()

    monkeypatch.setattr(
        "backend.checks.aryanoble.daily_arbel.boto3.Session",
        lambda *args, **kwargs: _SessionStub(),
    )

    result = checker.check("cis-erha", "451916275465")

    assert calls == ["ec2"]
    assert result.get("service_type") == "ec2"


def test_check_rds_scope_skips_primary_ec2_account(monkeypatch):
    checker = DailyArbelChecker(
        region="ap-southeast-3", window_hours=3, section_scope="rds"
    )
    calls = []

    monkeypatch.setattr(
        checker,
        "_resolve_account_config",
        lambda profile, account_id: {
            "account_name": "HRIS",
            "service_type": "ec2",
            "instances": {"app": "i-hris-1"},
            "metrics": ["CPUUtilization"],
            "thresholds": {"CPUUtilization": 75},
            "extra_sections": [],
        },
    )
    monkeypatch.setattr(
        checker,
        "_collect_section_report",
        lambda session, cw, profile, cfg: (
            calls.append(cfg.get("service_type")) or {},
            False,
        ),
    )

    class _SessionStub:
        def client(self, service_name, region_name=None):
            _ = service_name, region_name
            return object()

    monkeypatch.setattr(
        "backend.checks.aryanoble.daily_arbel.boto3.Session",
        lambda *args, **kwargs: _SessionStub(),
    )

    result = checker.check("HRIS", "774206556800")

    assert calls == []
    assert result.get("status") == "skipped"
    assert result.get("reason") == "section_scope_not_configured"


def test_sections_kwarg_bypasses_yaml_and_account_config():
    """When sections kwarg is provided, _resolve_account_config uses it directly."""
    checker = DailyArbelChecker(
        sections=[
            {
                "section_name": "Test RDS",
                "service_type": "rds",
                "cluster_id": "test-cluster",
                "instances": {"primary": "test-rds-instance"},
                "metrics": ["CPUUtilization", "FreeableMemory"],
                "thresholds": {"CPUUtilization": 80, "FreeableMemory": 1073741824},
                "alarm_thresholds": {},
            }
        ]
    )

    cfg = checker._resolve_account_config("unknown-profile", "000000000000")

    assert cfg is not None
    assert cfg["cluster_id"] == "test-cluster"
    assert cfg["instances"] == {"primary": "test-rds-instance"}
    assert cfg["thresholds"]["CPUUtilization"] == 80
    assert cfg["service_type"] == "rds"
    assert cfg["extra_sections"] == []


def test_sections_kwarg_with_extra_sections():
    """Second+ sections become extra_sections."""
    checker = DailyArbelChecker(
        sections=[
            {
                "section_name": "Main RDS",
                "service_type": "rds",
                "instances": {"primary": "rds-instance"},
                "metrics": ["FreeableMemory"],
                "thresholds": {},
            },
            {
                "section_name": "Extra EC2",
                "service_type": "ec2",
                "instances": {"webserver": "i-abc123"},
                "metrics": ["CPUUtilization"],
                "thresholds": {"CPUUtilization": 70},
            },
        ]
    )

    cfg = checker._resolve_account_config("any-profile", "111111111111")

    assert cfg["section_name"] == "Main RDS"
    assert len(cfg["extra_sections"]) == 1
    assert cfg["extra_sections"][0]["section_name"] == "Extra EC2"
