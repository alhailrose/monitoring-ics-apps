# tests/integration/test_aryanoble_backup_integration.py
import pytest
from datetime import datetime, timezone, timedelta


def test_aryanoble_backup_integration_simple():
    """Integration test for Aryanoble backup report generation"""
    from src.core.runtime.reports import build_whatsapp_backup_aryanoble

    # Mock realistic backup results
    jakarta_tz = timezone(timedelta(hours=7))

    mock_results = {
        "erha-buddy": {
            "backup": {
                "profile": "erha-buddy",
                "account_id": "486250145105",
                "total_jobs": 2,
                "completed_jobs": 2,
                "failed_jobs": 0,
                "expired_jobs": 0,
                "vaults": [],
                "issues": [],
                "job_details": [],
            }
        },
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
                        "job_id": "job-failed-1",
                        "state": "FAILED",
                        "resource_label": "i-0b8cf937001bcc2f9",
                        "created_wib": datetime(
                            2026, 3, 17, 0, 0, 0, tzinfo=jakarta_tz
                        ),
                        "reason": "The instance i-0b8cf937001bcc2f9 is not available",
                    }
                ],
            }
        },
        "arbel-master": {
            "backup": {
                "profile": "arbel-master",
                "account_id": "477153214925",
                "total_jobs": 1,
                "completed_jobs": 1,
                "failed_jobs": 0,
                "expired_jobs": 0,
                "vaults": [],
                "issues": [],
                "job_details": [],
            }
        },
    }

    # Test the formatter directly
    result = build_whatsapp_backup_aryanoble("17-03-2026", mock_results)

    # Verify Aryanoble format elements are present
    assert "Selamat Pagi Team," in result
    assert "Berikut report untuk AryaNoble Backup pada hari ini" in result
    assert "17-03-2026" in result
    assert "Completed:" in result
    assert "ERHA BUDDY - 486250145105" in result
    assert "Failed:" in result
    assert "Genero Manufacture - 798344624633" in result
    assert "Detail 1:" in result
    assert "Resource: i-0b8cf937001bcc2f9" in result
    assert "Time: 17-03-2026 00:00 WIB" in result
    assert "Reason: The instance i-0b8cf937001bcc2f9 is not available" in result

    # Verify arbel-master is excluded
    assert "Arbel Master" not in result
    assert "477153214925" not in result
