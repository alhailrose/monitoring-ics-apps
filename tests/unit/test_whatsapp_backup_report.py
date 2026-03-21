from datetime import datetime, timedelta, timezone

from backend.domain.runtime.reports import build_whatsapp_backup, summarize_backup_whatsapp


def test_backup_report_has_success_headline_when_all_accounts_healthy():
    all_results = {
        "connect-prod": {
            "backup": {
                "status": "success",
                "total_jobs": 1,
                "failed_jobs": 0,
                "expired_jobs": 0,
                "vaults": [],
                "rds_snapshots_24h": 0,
                "issues": [],
                "job_details": [],
            }
        }
    }

    text = build_whatsapp_backup("19-02-2026", all_results)

    assert "Status Utama: ✅ Semua akun backup sukses" in text
    assert "Akun Bermasalah" not in text
    assert "Detail per akun:" in text


def test_backup_report_highlights_failed_accounts_clearly():
    ts = datetime(2026, 2, 19, 9, 0, tzinfo=timezone(timedelta(hours=7)))
    all_results = {
        "connect-prod": {
            "backup": {
                "status": "success",
                "total_jobs": 2,
                "failed_jobs": 2,
                "expired_jobs": 0,
                "vaults": [],
                "rds_snapshots_24h": 0,
                "issues": ["2 failed jobs"],
                "job_details": [
                    {
                        "state": "FAILED",
                        "resource_label": "rds-instance-a",
                        "created_wib": ts,
                        "reason": "Snapshot timeout",
                    },
                    {
                        "state": "FAILED",
                        "resource_label": "rds-instance-b",
                        "created_wib": ts,
                        "reason": "Access denied",
                    },
                ],
            }
        }
    }

    text = build_whatsapp_backup("19-02-2026", all_results)

    assert "Status Utama: ⚠️ Ada akun backup gagal/perlu perhatian" in text
    assert "Akun Bermasalah:" in text
    assert "❌ Connect Prod - 620463044477" in text
    assert "2 job FAILED" in text


def test_backup_summary_exposes_all_success_flag_and_failed_profiles():
    all_results = {
        "connect-prod": {
            "backup": {
                "status": "success",
                "total_jobs": 1,
                "failed_jobs": 1,
                "expired_jobs": 0,
                "issues": ["1 failed job(s)"],
                "vaults": [],
            }
        },
        "centralized-s3": {
            "backup": {
                "status": "success",
                "total_jobs": 3,
                "failed_jobs": 0,
                "expired_jobs": 0,
                "issues": [],
                "vaults": [],
            }
        },
    }

    summary = summarize_backup_whatsapp(all_results)

    assert summary["all_success"] is False
    assert summary["total_accounts"] == 2
    assert summary["problem_accounts_count"] == 1
    assert summary["problem_accounts"][0]["profile"] == "connect-prod"
