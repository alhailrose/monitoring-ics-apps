import subprocess

from src.checks.huawei.ecs_utilization import (
    HuaweiECSUtilizationChecker,
    HcloudCli,
    classify_memory_behavior,
)


def test_classify_memory_behavior_high_stable():
    row = {"latest": 77.5, "avg_12h": 77.2, "peak": 77.9}
    assert classify_memory_behavior(row, 70.0) == "HIGH_STABLE"


def test_classify_memory_behavior_spike():
    row = {"latest": 70.6, "avg_12h": 71.0, "peak": 85.6}
    assert classify_memory_behavior(row, 70.0) == "SPIKE"


def test_format_report_contains_compact_note_paragraph():
    checker = HuaweiECSUtilizationChecker()
    report = checker.format_report(
        {
            "status": "success",
            "account": "dh_prod_nonerp",
            "rise_threshold": 70.0,
            "util": {
                "cpu_avg_12h": 4.34,
                "cpu_peak_overall": {"name": "Mobile-Middleware-Prod", "peak": 63.85},
                "mem_avg_12h": 25.67,
                "mem_peak_overall": {
                    "name": "Corporate-Website-DB-Dev",
                    "peak": 85.6,
                    "rise_start_ms": 1772653500000,
                    "peak_time_ms": 1772654700000,
                    "latest": 70.6,
                    "avg_12h": 71.0,
                },
                "top_mem_hot": [
                    {
                        "name": "Corporate-Website-DB-Dev",
                        "peak": 85.6,
                        "behavior": "SPIKE",
                    }
                ],
            },
        }
    )
    assert "Daily Monitoring Utilisasi ECS Darmahenwa" in report
    assert "Catatan:" in report
    assert "[BLOCK - SPIKE / IDLE TINGGI]" not in report


def test_hcloud_cli_injects_timeout_and_retry_flags(monkeypatch):
    captured = {}

    class _Proc:
        returncode = 0
        stdout = '{"ok": true}'
        stderr = ""

    def _fake_run(cmd, stdout, stderr, text, timeout=None):
        captured["cmd"] = cmd
        return _Proc()

    monkeypatch.setattr("src.checks.huawei.ecs_utilization.subprocess.run", _fake_run)

    cli = HcloudCli()
    data, err = cli.run_json(["CES", "ListMetrics", "--cli-profile=demo"])

    assert err is None
    assert data == {"ok": True}
    assert "--cli-read-timeout=30" in captured["cmd"]
    assert "--cli-connect-timeout=10" in captured["cmd"]
    assert "--cli-retry-count=2" in captured["cmd"]


def test_hcloud_cli_retries_once_on_timeout_error(monkeypatch):
    calls = {"count": 0}

    class _ErrProc:
        returncode = 1
        stdout = ""
        stderr = "[OPENAPI_ERROR] API calling timed out"

    class _OkProc:
        returncode = 0
        stdout = '{"servers": []}'
        stderr = ""

    def _fake_run(_cmd, stdout, stderr, text, timeout=None):
        calls["count"] += 1
        if calls["count"] == 1:
            return _ErrProc()
        return _OkProc()

    monkeypatch.setattr("src.checks.huawei.ecs_utilization.subprocess.run", _fake_run)

    cli = HcloudCli()
    data, err = cli.run_json(["ECS", "ListServersDetails", "--cli-profile=demo"])

    assert err is None
    assert data == {"servers": []}
    assert calls["count"] == 2


def test_hcloud_cli_falls_back_without_transport_flags_when_unsupported(monkeypatch):
    calls = []

    class _InvalidParamProc:
        returncode = 1
        stdout = ""
        stderr = "[USE_ERROR]Invalid parameter: cli-read-timeout"

    class _OkProc:
        returncode = 0
        stdout = '{"servers": []}'
        stderr = ""

    def _fake_run(cmd, stdout, stderr, text, timeout=None):
        calls.append(cmd)
        if len(calls) == 1:
            return _InvalidParamProc()
        return _OkProc()

    monkeypatch.setattr("src.checks.huawei.ecs_utilization.subprocess.run", _fake_run)

    cli = HcloudCli()
    data, err = cli.run_json(["ECS", "ListServersDetails", "--cli-profile=demo"])

    assert err is None
    assert data == {"servers": []}
    assert len(calls) == 2
    assert "--cli-read-timeout=30" in calls[0]
    assert "--cli-connect-timeout=10" in calls[0]
    assert "--cli-retry-count=2" in calls[0]
    assert "--cli-read-timeout=30" not in calls[1]
    assert "--cli-connect-timeout=10" not in calls[1]
    assert "--cli-retry-count=2" not in calls[1]


def test_hcloud_cli_returns_timeout_error_when_subprocess_hangs(monkeypatch):
    calls = {"count": 0}

    def _fake_run(*_args, **_kwargs):
        calls["count"] += 1
        raise subprocess.TimeoutExpired(cmd="hcloud", timeout=45)

    monkeypatch.setattr("src.checks.huawei.ecs_utilization.subprocess.run", _fake_run)

    cli = HcloudCli(max_attempts=2)
    data, err = cli.run_json(["ECS", "ListServersDetails", "--cli-profile=demo"])

    assert data is None
    assert err is not None
    assert "timed out" in err.lower()
    assert calls["count"] == 2


def test_list_server_map_fetches_all_pages(monkeypatch):
    checker = HuaweiECSUtilizationChecker()
    calls = []

    def _fake_run_json(args):
        calls.append(args)
        offset = "1"
        for a in args:
            if a.startswith("--offset="):
                offset = a.split("=", 1)[1]
                break

        if offset == "1":
            return {
                "count": 3,
                "servers": [
                    {"id": "i-1", "name": "srv-1", "status": "ACTIVE"},
                    {"id": "i-2", "name": "srv-2", "status": "ACTIVE"},
                ],
            }, None

        if offset == "2":
            return {
                "count": 3,
                "servers": [
                    {"id": "i-3", "name": "srv-3", "status": "SHUTOFF"},
                ],
            }, None

        return {"count": 3, "servers": []}, None

    monkeypatch.setattr(checker, "cli", type("_Cli", (), {"run_json": staticmethod(_fake_run_json)})())

    server_map, err = checker._list_server_map("demo-profile", "ap-southeast-4")

    assert err is None
    assert sorted(server_map.keys()) == ["i-1", "i-2", "i-3"]
    assert len(calls) >= 2


def test_list_metrics_fetches_all_pages_with_start_marker(monkeypatch):
    checker = HuaweiECSUtilizationChecker()
    calls = []

    first_marker = "AGT.ECS.mem_usedPercent.instance_id:i-2.index:2"

    def _fake_run_json(args):
        calls.append(args)
        start_token = None
        for a in args:
            if a.startswith("--start="):
                start_token = a.split("=", 1)[1]
                break

        if start_token is None:
            return {
                "metrics": [
                    {"dimensions": [{"name": "instance_id", "value": "i-1"}]},
                    {"dimensions": [{"name": "instance_id", "value": "i-2"}]},
                ],
                "meta_data": {"total": 3, "marker": first_marker},
            }, None

        if start_token == first_marker:
            return {
                "metrics": [
                    {"dimensions": [{"name": "instance_id", "value": "i-3"}]},
                ],
                "meta_data": {"total": 3, "marker": "AGT.ECS.mem_usedPercent.instance_id:i-3.index:3"},
            }, None

        return {"metrics": [], "meta_data": {"total": 3}}, None

    monkeypatch.setattr(checker, "cli", type("_Cli", (), {"run_json": staticmethod(_fake_run_json)})())

    metrics = checker._list_metrics("demo-profile", "ap-southeast-4", "AGT.ECS", "mem_usedPercent")

    assert len(metrics) == 3
    assert len(calls) >= 2
