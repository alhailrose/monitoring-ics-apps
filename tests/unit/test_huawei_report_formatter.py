from src.core.formatting.reports import (
    build_huawei_utilization_customer_report,
    classify_huawei_memory_behavior,
)


def test_classify_huawei_memory_behavior_stable():
    row = {"latest": 77.5, "avg_12h": 77.2, "peak": 77.9}
    assert classify_huawei_memory_behavior(row, 70.0) == "HIGH_STABLE"


def test_build_huawei_utilization_customer_report_includes_block():
    report = build_huawei_utilization_customer_report(
        {
            "status": "success",
            "account": "dh_prod_nonerp",
            "rise_threshold": 70.0,
            "util_window": {"to": "2026-03-05 12:23:09 WIB"},
            "util": {
                "cpu_avg_12h": 4.34,
                "cpu_peak_overall": {"name": "Mobile-Middleware-Prod", "peak": 63.85},
                "mem_avg_12h": 25.67,
                "mem_peak_overall": {
                    "name": "Corporate-Website-DB-Dev",
                    "peak": 85.6,
                    "latest": 70.6,
                    "avg_12h": 71.0,
                    "rise_start_ms": 1772653500000,
                    "peak_time_ms": 1772654700000,
                },
                "top_mem_hot": [
                    {
                        "name": "Corporate-Website-DB-Dev",
                        "peak": 85.6,
                        "latest": 70.6,
                        "avg_12h": 71.0,
                    }
                ],
            },
        }
    )
    assert "Daily Monitoring Utilisasi ECS Darmahenwa" in report
    assert "[BLOCK - SPIKE / IDLE TINGGI]" in report
