from backend.domain.formatting.reports import (
    build_huawei_legacy_consolidated_report,
    build_huawei_legacy_whatsapp_report,
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
    assert "Catatan:" in report
    assert "[BLOCK - SPIKE / IDLE TINGGI]" not in report


def test_build_huawei_legacy_consolidated_report_contains_numbered_accounts_and_note():
    all_results = {
        "dh_prod_nonerp-ro": {
            "status": "success",
            "account": "dh_prod_nonerp",
            "rise_threshold": 70.0,
            "util_window": {"to": "2026-03-06 10:00:00 WIB"},
            "util": {
                "cpu_avg_12h": 3.4,
                "cpu_peak_overall": {"name": "app-1", "peak": 10.0},
                "mem_avg_12h": 23.4,
                "mem_peak_overall": {"name": "db-1", "peak": 40.1, "avg_12h": 23.4},
                "top_mem_hot": [],
            },
        },
        "afco_prod_erp-ro": {
            "status": "error",
            "profile": "afco_prod_erp-ro",
            "error": "timeout",
        },
    }
    errors = [("afco_prod_erp-ro", "timeout")]

    text = build_huawei_legacy_consolidated_report(
        all_results,
        errors,
        ["dh_prod_nonerp-ro", "afco_prod_erp-ro"],
    )

    assert "Daily Monitoring Utilisasi ECS Darmahenwa" in text
    assert "1. dh_prod_nonerp" in text
    assert "2. afco_prod_erp" in text
    assert "Catatan:" in text
    assert "[BLOCK - SPIKE / IDLE TINGGI]" not in text
    assert "stabil tinggi terus" in text
    assert "spike" in text
    assert "HIGH-STABLE" not in text
    assert "IDLE tinggi" not in text


def test_build_huawei_legacy_consolidated_report_summarizes_no_data_accounts_at_bottom():
    all_results = {
        "dh_log-ro": {
            "status": "success",
            "account": "dh_log",
            "rise_threshold": 70.0,
            "util_window": {"to": "2026-03-06 10:00:00 WIB"},
            "util": {
                "cpu_avg_12h": None,
                "cpu_peak_overall": None,
                "mem_avg_12h": None,
                "mem_peak_overall": None,
                "top_mem_hot": [],
            },
        },
        "dh_prod_nonerp-ro": {
            "status": "success",
            "account": "dh_prod_nonerp",
            "rise_threshold": 70.0,
            "util_window": {"to": "2026-03-06 10:00:00 WIB"},
            "util": {
                "cpu_avg_12h": 3.0,
                "cpu_peak_overall": {"name": "app-1", "peak": 10.0},
                "mem_avg_12h": 30.0,
                "mem_peak_overall": {"name": "db-1", "peak": 40.0, "avg_12h": 30.0},
                "top_mem_hot": [],
            },
        },
    }

    text = build_huawei_legacy_consolidated_report(
        all_results,
        errors=[],
        ordered_profiles=["dh_log-ro", "dh_prod_nonerp-ro"],
    )

    assert "Akun tanpa data utilisasi:" in text
    assert "- dh_log" in text
    assert "dh_prod_nonerp" not in text.split("Akun tanpa data utilisasi:", 1)[1]


def test_build_huawei_legacy_consolidated_report_does_not_promote_spike_as_alert():
    all_results = {
        "dh_prod_nonerp-ro": {
            "status": "success",
            "account": "dh_prod_nonerp",
            "rise_threshold": 70.0,
            "util_window": {"to": "2026-03-06 10:00:00 WIB"},
            "util": {
                "cpu_avg_12h": 4.0,
                "cpu_peak_overall": {"name": "app-1", "peak": 8.0},
                "mem_avg_12h": 35.0,
                "mem_peak_overall": {
                    "name": "db-1",
                    "peak": 86.1,
                    "latest": 41.0,
                    "avg_12h": 35.0,
                    "rise_start_ms": 1772653500000,
                    "peak_time_ms": 1772654100000,
                },
                "top_mem_hot": [
                    {
                        "name": "db-1",
                        "peak": 86.1,
                        "latest": 41.0,
                        "avg_12h": 35.0,
                        "behavior": "SPIKE",
                    }
                ],
            },
        }
    }

    text = build_huawei_legacy_consolidated_report(
        all_results,
        errors=[],
        ordered_profiles=["dh_prod_nonerp-ro"],
    )

    assert "Terdapat usage tinggi sesaat (spike)" in text
    assert "- SPIKE:" not in text


def test_build_huawei_legacy_whatsapp_report_compact_and_neat():
    all_results = {
        "dh_prod_nonerp-ro": {
            "status": "success",
            "account": "dh_prod_nonerp",
            "rise_threshold": 70.0,
            "util_window": {"to": "2026-03-06 10:00:00 WIB"},
            "util": {
                "cpu_avg_12h": 3.4,
                "cpu_peak_overall": {"name": "app-1", "peak": 10.0},
                "mem_avg_12h": 72.0,
                "mem_peak_overall": {
                    "name": "db-1",
                    "peak": 75.0,
                    "avg_12h": 72.0,
                    "latest": 74.5,
                },
                "top_mem_hot": [{"name": "db-1", "peak": 75.0, "behavior": "HIGH_STABLE"}],
            },
        },
        "afco_prod_erp-ro": {"status": "error", "error": "timeout"},
    }

    text = build_huawei_legacy_whatsapp_report(
        all_results=all_results,
        errors=[("afco_prod_erp-ro", "timeout")],
        ordered_profiles=["dh_prod_nonerp-ro", "afco_prod_erp-ro", "dh_log-ro"],
    )

    assert "*Daily Monitoring Utilisasi ECS Darmahenwa*" in text
    assert "1) *dh_prod_nonerp*" in text
    assert "2) *afco_prod_erp*: ERROR - timeout." in text
    assert "Tanpa data utilisasi: dh_log." in text
    assert "stabil tinggi terus" in text
    assert "spike" in text
    assert "HIGH-STABLE" not in text
    assert "IDLE tinggi" not in text
