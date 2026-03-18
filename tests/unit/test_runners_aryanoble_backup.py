import pytest
from unittest.mock import patch, MagicMock
from src.core.runtime.runners import run_group_specific


def test_aryanoble_uses_custom_backup_formatter():
    """Test that Aryanoble customer uses custom backup formatter"""

    # Mock the backup results
    mock_backup_result = {
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

    with (
        patch("src.core.runtime.runners._check_single_profile") as mock_check,
        patch(
            "src.core.runtime.reports.build_whatsapp_backup_aryanoble"
        ) as mock_aryanoble_formatter,
        patch(
            "src.core.runtime.runners.build_whatsapp_backup"
        ) as mock_default_formatter,
        patch("src.core.runtime.runners.print_group_header"),
        patch("src.core.runtime.runners.console"),
        patch("builtins.print"),
    ):
        # Setup mocks
        mock_check.return_value = mock_backup_result
        mock_aryanoble_formatter.return_value = "Aryanoble custom format"
        mock_default_formatter.return_value = "Default format"

        # Call function with Aryanoble group
        run_group_specific("backup", ["erha-buddy"], "ap-southeast-3", "Aryanoble")

        # Verify Aryanoble formatter was called, not default
        mock_aryanoble_formatter.assert_called_once()
        mock_default_formatter.assert_not_called()


def test_non_aryanoble_uses_default_backup_formatter():
    """Test that non-Aryanoble customers use default backup formatter"""

    # Mock the backup results
    mock_backup_result = {
        "profile": "some-profile",
        "account_id": "123456789",
        "total_jobs": 1,
        "completed_jobs": 1,
        "failed_jobs": 0,
        "expired_jobs": 0,
        "vaults": [],
        "issues": [],
        "job_details": [],
    }

    with (
        patch("src.core.runtime.runners._check_single_profile") as mock_check,
        patch(
            "src.core.runtime.reports.build_whatsapp_backup_aryanoble"
        ) as mock_aryanoble_formatter,
        patch(
            "src.core.runtime.runners.build_whatsapp_backup"
        ) as mock_default_formatter,
        patch("src.core.runtime.runners.print_group_header"),
        patch("src.core.runtime.runners.console"),
        patch("builtins.print"),
    ):
        # Setup mocks
        mock_check.return_value = mock_backup_result
        mock_aryanoble_formatter.return_value = "Aryanoble custom format"
        mock_default_formatter.return_value = "Default format"

        # Call function with non-Aryanoble group
        run_group_specific(
            "backup", ["some-profile"], "ap-southeast-3", "SomeOtherCustomer"
        )

        # Verify default formatter was called, not Aryanoble
        mock_default_formatter.assert_called_once()
        mock_aryanoble_formatter.assert_not_called()
