from datetime import datetime, timezone, timedelta

from src.core.runtime.reports import build_whatsapp_backup


def test_backup_report_keeps_failed_and_expired_sections_at_end_when_empty():
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

    assert "Completed:\r\n- Connect Prod - 620463044477" in text
    assert text.endswith("Expired:\r\n- (tidak ada)")


def test_backup_report_groups_failed_details_by_account():
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

    assert "Failed:\r\n- Connect Prod - 620463044477" in text
    assert "Detail 1:" in text
    assert "Resource: rds-instance-a" in text
    assert "Detail 2:" in text
    assert "Resource: rds-instance-b" in text
