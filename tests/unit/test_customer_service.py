"""Tests for CustomerService.import_from_yaml field extraction."""
import pytest
from unittest.mock import MagicMock, call


ARYANOBLE_YAML = {
    "customer_id": "aryanoble",
    "display_name": "Aryanoble",
    "sso_session": "aryanoble-sso",
    "checks": ["daily-arbel", "daily-budget", "backup"],
    "slack": {"webhook_url": "https://hooks.slack.com/test", "channel": "#ops", "enabled": True},
    "accounts": [
        {
            "profile": "connect-prod",
            "account_id": "620463044477",
            "display_name": "CONNECT Prod",
            "alarm_names": ["alarm-1", "alarm-2"],
            "region": "ap-southeast-3",
            "daily_arbel": {"cluster_id": "noncis-prod-rds"},
        },
        {
            "profile": "cis-erha",
            "account_id": "451916275465",
            "display_name": "CIS ERHA",
            "alarm_names": ["cis-alarm-1"],
            # No region — should be None
        },
    ],
}


def _make_service(existing_customer=None, existing_accounts=None):
    """Build CustomerService with fully mocked repo."""
    repo = MagicMock()
    repo.get_customer_by_name.return_value = existing_customer
    if existing_customer is None:
        fake_customer = MagicMock()
        fake_customer.id = "cust-uuid-1"
        fake_customer.name = "aryanoble"
        repo.create_customer.return_value = fake_customer
    else:
        fake_customer = existing_customer

    repo.get_accounts_by_customer.return_value = existing_accounts or []

    from backend.domain.services.customer_service import CustomerService
    svc = CustomerService(repo)
    return svc, repo, fake_customer


def test_import_from_yaml_passes_checks():
    svc, repo, _ = _make_service()
    svc.import_from_yaml(ARYANOBLE_YAML)
    repo.create_customer.assert_called_once()
    call_kwargs = repo.create_customer.call_args
    assert call_kwargs.kwargs.get("checks") == ["daily-arbel", "daily-budget", "backup"]


def test_import_from_yaml_passes_sso_session():
    svc, repo, _ = _make_service()
    svc.import_from_yaml(ARYANOBLE_YAML)
    call_kwargs = repo.create_customer.call_args
    assert call_kwargs.kwargs.get("sso_session") == "aryanoble-sso"


def test_import_from_yaml_passes_alarm_names_per_account():
    svc, repo, _ = _make_service()
    svc.import_from_yaml(ARYANOBLE_YAML)
    # First account: connect-prod — should have alarm_names
    add_calls = repo.add_account.call_args_list
    connect_call = next(c for c in add_calls if c.kwargs.get("profile_name") == "connect-prod")
    assert connect_call.kwargs.get("alarm_names") == ["alarm-1", "alarm-2"]


def test_import_from_yaml_passes_region_per_account():
    svc, repo, _ = _make_service()
    svc.import_from_yaml(ARYANOBLE_YAML)
    add_calls = repo.add_account.call_args_list
    connect_call = next(c for c in add_calls if c.kwargs.get("profile_name") == "connect-prod")
    assert connect_call.kwargs.get("region") == "ap-southeast-3"


def test_import_from_yaml_region_none_when_not_in_yaml():
    svc, repo, _ = _make_service()
    svc.import_from_yaml(ARYANOBLE_YAML)
    add_calls = repo.add_account.call_args_list
    cis_call = next(c for c in add_calls if c.kwargs.get("profile_name") == "cis-erha")
    assert cis_call.kwargs.get("region") is None


def test_import_from_yaml_preserves_daily_arbel_in_config_extra():
    svc, repo, _ = _make_service()
    svc.import_from_yaml(ARYANOBLE_YAML)
    add_calls = repo.add_account.call_args_list
    connect_call = next(c for c in add_calls if c.kwargs.get("profile_name") == "connect-prod")
    config_extra = connect_call.kwargs.get("config_extra") or {}
    assert config_extra.get("daily_arbel") == {"cluster_id": "noncis-prod-rds"}
