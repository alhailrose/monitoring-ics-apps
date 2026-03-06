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


def test_format_report_contains_block():
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
    assert "[BLOCK - SPIKE / IDLE TINGGI]" in report
    assert "SPIKE" in report


def test_hcloud_cli_injects_timeout_and_retry_flags(monkeypatch):
    captured = {}

    class _Proc:
        returncode = 0
        stdout = '{"ok": true}'
        stderr = ""

    def _fake_run(cmd, stdout, stderr, text):
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

    def _fake_run(_cmd, stdout, stderr, text):
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
