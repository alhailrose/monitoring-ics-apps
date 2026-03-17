from datetime import datetime, timedelta, timezone

from src.checks.generic.aws_utilization_3core import AWSUtilization3CoreChecker


def test_collect_instance_metrics_returns_partial_data_when_memory_missing(monkeypatch):
    checker = AWSUtilization3CoreChecker()
    now = datetime.now(timezone.utc)

    monkeypatch.setattr(
        checker, "_get_cpu_usage", lambda *_args, **_kwargs: (30.0, 50.0)
    )
    monkeypatch.setattr(
        checker, "_get_memory_usage", lambda *_args, **_kwargs: (None, None, None)
    )
    monkeypatch.setattr(checker, "_get_disk_free_min", lambda *_args, **_kwargs: 55.0)

    class _Session:
        def client(self, *_args, **_kwargs):
            return object()

    row = checker._collect_instance_metrics(
        session=_Session(),
        instance={
            "instance_id": "i-123",
            "name": "web-a",
            "state": "running",
            "os_type": "linux",
            "region": "ap-southeast-3",
        },
        start_time=now - timedelta(hours=12),
        end_time=now,
    )

    assert row["memory_avg_12h"] is None
    assert row["memory_peak_12h"] is None
    assert row["status"] == "PARTIAL_DATA"


def test_get_memory_usage_uses_windows_metric_name():
    checker = AWSUtilization3CoreChecker()

    class _CloudWatch:
        def list_metrics(self, Namespace, MetricName, Dimensions):
            if (
                Namespace == "CWAgent"
                and MetricName == "Memory % Committed Bytes In Use"
            ):
                return {
                    "Metrics": [
                        {
                            "Dimensions": [
                                {"Name": "InstanceId", "Value": Dimensions[0]["Value"]},
                                {"Name": "objectname", "Value": "Memory"},
                            ]
                        }
                    ]
                }
            return {"Metrics": []}

        def get_metric_statistics(
            self,
            Namespace,
            MetricName,
            Dimensions,
            StartTime,
            EndTime,
            Period,
            Statistics,
        ):
            return {"Datapoints": [{"Average": 55.0}, {"Average": 70.0}]}

    avg_val, peak_val, metric_name = checker._get_memory_usage(
        _CloudWatch(),
        instance_id="i-win",
        os_type="windows",
        start_time=datetime.now(timezone.utc) - timedelta(hours=12),
        end_time=datetime.now(timezone.utc),
    )

    assert avg_val == 62.5
    assert peak_val == 70.0
    assert metric_name == "Memory % Committed Bytes In Use"


def test_get_disk_free_min_calculates_from_disk_used_percent():
    checker = AWSUtilization3CoreChecker()

    class _CloudWatch:
        def list_metrics(self, Namespace, MetricName, Dimensions):
            return {
                "Metrics": [
                    {
                        "Dimensions": [
                            {"Name": "InstanceId", "Value": Dimensions[0]["Value"]},
                            {"Name": "path", "Value": "/"},
                        ]
                    },
                    {
                        "Dimensions": [
                            {"Name": "InstanceId", "Value": Dimensions[0]["Value"]},
                            {"Name": "path", "Value": "/data"},
                        ]
                    },
                ]
            }

        def get_metric_statistics(
            self,
            Namespace,
            MetricName,
            Dimensions,
            StartTime,
            EndTime,
            Period,
            Statistics,
        ):
            path = next((x["Value"] for x in Dimensions if x["Name"] == "path"), "")
            if path == "/":
                return {"Datapoints": [{"Average": 65.0}, {"Average": 90.0}]}
            return {"Datapoints": [{"Average": 55.0}, {"Average": 60.0}]}

    disk_free_min = checker._get_disk_free_min(
        _CloudWatch(),
        instance_id="i-disk",
        start_time=datetime.now(timezone.utc) - timedelta(hours=12),
        end_time=datetime.now(timezone.utc),
    )

    assert disk_free_min == 10.0


def test_get_disk_free_min_ignores_squashfs_snap_mounts():
    checker = AWSUtilization3CoreChecker()

    class _CloudWatch:
        def list_metrics(self, Namespace, MetricName, Dimensions):
            return {
                "Metrics": [
                    {
                        "Dimensions": [
                            {"Name": "InstanceId", "Value": Dimensions[0]["Value"]},
                            {"Name": "path", "Value": "/snap/core22/2339"},
                            {"Name": "fstype", "Value": "squashfs"},
                        ]
                    },
                    {
                        "Dimensions": [
                            {"Name": "InstanceId", "Value": Dimensions[0]["Value"]},
                            {"Name": "path", "Value": "/"},
                            {"Name": "fstype", "Value": "ext4"},
                        ]
                    },
                ]
            }

        def get_metric_statistics(
            self,
            Namespace,
            MetricName,
            Dimensions,
            StartTime,
            EndTime,
            Period,
            Statistics,
        ):
            path = next((x["Value"] for x in Dimensions if x["Name"] == "path"), "")
            if path.startswith("/snap/"):
                return {"Datapoints": [{"Average": 100.0}]}
            return {"Datapoints": [{"Average": 35.0}]}

    disk_free_min = checker._get_disk_free_min(
        _CloudWatch(),
        instance_id="i-prod",
        start_time=datetime.now(timezone.utc) - timedelta(hours=12),
        end_time=datetime.now(timezone.utc),
    )

    assert disk_free_min == 65.0


def test_check_collects_per_instance_rows(monkeypatch):
    checker = AWSUtilization3CoreChecker()

    monkeypatch.setattr(checker, "_create_session", lambda _profile: object())
    monkeypatch.setattr(
        checker,
        "_discover_regions",
        lambda _session, profile=None: ["ap-southeast-3"],
    )
    monkeypatch.setattr(
        checker,
        "_list_instances",
        lambda _session, _regions: [
            {
                "instance_id": "i-1",
                "name": "app-1",
                "state": "running",
                "os_type": "linux",
                "region": "ap-southeast-3",
            },
            {
                "instance_id": "i-2",
                "name": "app-2",
                "state": "running",
                "os_type": "windows",
                "region": "ap-southeast-3",
            },
        ],
    )

    def _fake_collect(_session, instance, _start_time, _end_time):
        if instance["instance_id"] == "i-1":
            return {
                **instance,
                "cpu_avg_12h": 20.0,
                "cpu_peak_12h": 30.0,
                "memory_avg_12h": 40.0,
                "memory_peak_12h": 50.0,
                "memory_metric": "mem_used_percent",
                "disk_free_min_percent": 60.0,
                "status": "NORMAL",
            }
        return {
            **instance,
            "cpu_avg_12h": 55.0,
            "cpu_peak_12h": 88.0,
            "memory_avg_12h": None,
            "memory_peak_12h": None,
            "memory_metric": None,
            "disk_free_min_percent": 15.0,
            "status": "CRITICAL",
        }

    monkeypatch.setattr(checker, "_collect_instance_metrics", _fake_collect)

    result = checker.check("demo", "111111111111")

    assert result["status"] == "success"
    assert len(result["instances"]) == 2
    assert result["summary"]["normal"] == 1
    assert result["summary"]["critical"] == 1


def test_discover_regions_prefers_profile_regions_configured():
    checker = AWSUtilization3CoreChecker(
        profile_regions={"Techmeister": ["ap-southeast-1", "eu-central-1"]}
    )

    regions = checker._discover_regions(session=object(), profile="Techmeister")

    assert regions == ["ap-southeast-1", "eu-central-1"]


def test_list_instances_only_includes_running_instances():
    checker = AWSUtilization3CoreChecker()

    class _Paginator:
        def paginate(self):
            return [
                {
                    "Reservations": [
                        {
                            "Instances": [
                                {
                                    "InstanceId": "i-running",
                                    "State": {"Name": "running"},
                                    "Tags": [{"Key": "Name", "Value": "app-live"}],
                                },
                                {
                                    "InstanceId": "i-stopped",
                                    "State": {"Name": "stopped"},
                                    "Tags": [{"Key": "Name", "Value": "app-old"}],
                                },
                            ]
                        }
                    ]
                }
            ]

    class _EC2:
        def get_paginator(self, _name):
            return _Paginator()

    class _Session:
        def client(self, _service, region_name=None):
            return _EC2()

    rows = checker._list_instances(_Session(), ["ap-southeast-3"])

    assert len(rows) == 1
    assert rows[0]["instance_id"] == "i-running"
    assert rows[0]["name"] == "app-live"
