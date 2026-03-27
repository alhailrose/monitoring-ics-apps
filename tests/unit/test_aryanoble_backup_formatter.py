import pytest
from datetime import datetime, timezone, timedelta
from backend.domain.runtime.reports import build_whatsapp_backup_aryanoble


def test_aryanoble_backup_formatter_completed_only():
    """Test formatter with only completed accounts"""
    all_results = {
        "erha-buddy": {
            "backup": {
                "profile": "erha-buddy",
                "account_id": "486250145105",
                "total_jobs": 3,
                "completed_jobs": 3,
                "failed_jobs": 0,
                "expired_jobs": 0,
                "vaults": [],
                "issues": [],
                "job_details": [],
            }
        },
        "cis-erha": {
            "backup": {
                "profile": "cis-erha",
                "account_id": "451916275465",
                "total_jobs": 2,
                "completed_jobs": 2,
                "failed_jobs": 0,
                "expired_jobs": 0,
                "vaults": [],
                "issues": [],
                "job_details": [],
            }
        },
    }

    result = build_whatsapp_backup_aryanoble("17-03-2026", all_results)

    assert any(g in result for g in ("Selamat Pagi Team,", "Selamat Siang Team,", "Selamat Sore Team,", "Selamat Malam Team,"))
    assert "Berikut report untuk AryaNoble Backup pada hari ini" in result
    assert "17-03-2026" in result
    assert "Completed:" in result
    assert "ERHA BUDDY - 486250145105" in result
    assert "CIS Erha - 451916275465" in result
    assert "Failed:" in result
    assert "(tidak ada)" in result
    assert "Expired:" in result


def test_aryanoble_backup_formatter_with_failed_jobs():
    """Test formatter with failed backup jobs"""
    jakarta_tz = timezone(timedelta(hours=7))
    created_time = datetime(2026, 3, 17, 0, 0, 0, tzinfo=jakarta_tz)

    all_results = {
        "genero-manufacture": {
            "backup": {
                "profile": "genero-manufacture",
                "account_id": "798344624633",
                "total_jobs": 2,
                "completed_jobs": 1,
                "failed_jobs": 1,
                "expired_jobs": 0,
                "vaults": [],
                "issues": ["1 failed job(s)"],
                "job_details": [
                    {
                        "job_id": "job-123",
                        "state": "FAILED",
                        "resource_label": "i-0b8cf937001bcc2f9",
                        "created_wib": created_time,
                        "reason": "The instance i-0b8cf937001bcc2f9 is not available",
                    },
                    {
                        "job_id": "job-456",
                        "state": "COMPLETED",
                        "resource_label": "vol-abc123",
                        "created_wib": created_time,
                        "reason": "",
                    },
                ],
            }
        }
    }

    result = build_whatsapp_backup_aryanoble("17-03-2026", all_results)

    assert "Failed:" in result
    assert "Genero Manufacture - 798344624633" in result
    assert "Detail 1:" in result
    assert "Resource: i-0b8cf937001bcc2f9" in result
    assert "Time: 17-03-2026 00:00 WIB" in result
    assert "Reason: The instance i-0b8cf937001bcc2f9 is not available" in result
    assert "Completed:" in result
    assert "(tidak ada)" in result


def test_aryanoble_backup_formatter_excludes_arbel_master():
    """Test formatter excludes arbel-master account"""
    all_results = {
        "erha-buddy": {
            "backup": {
                "profile": "erha-buddy",
                "account_id": "486250145105",
                "total_jobs": 1,
                "completed_jobs": 1,
                "failed_jobs": 0,
                "expired_jobs": 0,
                "vaults": [],
                "issues": [],
                "job_details": [],
            }
        },
        "arbel-master": {
            "backup": {
                "profile": "arbel-master",
                "account_id": "477153214925",
                "total_jobs": 2,
                "completed_jobs": 2,
                "failed_jobs": 0,
                "expired_jobs": 0,
                "vaults": [],
                "issues": [],
                "job_details": [],
            }
        },
    }

    result = build_whatsapp_backup_aryanoble("17-03-2026", all_results)

    assert "ERHA BUDDY - 486250145105" in result
    assert "Arbel Master" not in result
    assert "477153214925" not in result
