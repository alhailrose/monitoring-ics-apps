from src.checks.huawei.ecs_utilization import (
    HuaweiECSUtilizationChecker,
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
