"""Tests for CheckExecutor per-account region and alarm_names injection."""
import pytest
from unittest.mock import MagicMock, patch


def _make_executor(default_region="ap-southeast-3"):
    from src.app.services.check_executor import CheckExecutor
    executor = CheckExecutor(
        check_repo=MagicMock(),
        customer_repo=MagicMock(),
        region=default_region,
        timeout=30,
    )
    return executor


def _make_account(profile_name, region=None, alarm_names=None, config_extra=None):
    acct = MagicMock()
    acct.profile_name = profile_name
    acct.region = region
    acct.alarm_names = alarm_names
    acct.config_extra = config_extra
    return acct


def test_execute_parallel_uses_account_region_when_set():
    executor = _make_executor(default_region="ap-southeast-3")
    acct = _make_account("bbi-prod", region="ap-southeast-1")

    with patch("src.app.services.check_executor._run_single_check") as mock_run:
        mock_run.return_value = {"status": "ok"}
        executor._execute_parallel([acct], {"cloudwatch": MagicMock()}, "ap-southeast-3")

    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    # _run_single_check(check_name, profile, region, check_kwargs)
    assert args[2] == "ap-southeast-1"


def test_execute_parallel_falls_back_to_effective_region_when_account_region_none():
    executor = _make_executor(default_region="ap-southeast-3")
    acct = _make_account("standard-prod", region=None)

    with patch("src.app.services.check_executor._run_single_check") as mock_run:
        mock_run.return_value = {"status": "ok"}
        executor._execute_parallel([acct], {"cloudwatch": MagicMock()}, "ap-southeast-3")

    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    assert args[2] == "ap-southeast-3"


def test_execute_parallel_injects_alarm_names_for_cloudwatch():
    executor = _make_executor()
    acct = _make_account("connect-prod", alarm_names=["alarm-a", "alarm-b"])

    with patch("src.app.services.check_executor._run_single_check") as mock_run:
        mock_run.return_value = {"status": "ok"}
        executor._execute_parallel([acct], {"cloudwatch": MagicMock()}, "ap-southeast-3")

    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    check_kwargs = args[3]
    assert check_kwargs is not None
    assert check_kwargs.get("alarm_names") == ["alarm-a", "alarm-b"]


def test_execute_parallel_does_not_inject_alarm_names_for_non_cloudwatch():
    executor = _make_executor()
    acct = _make_account("connect-prod", alarm_names=["alarm-a"])

    with patch("src.app.services.check_executor._run_single_check") as mock_run:
        mock_run.return_value = {"status": "ok"}
        executor._execute_parallel([acct], {"guardduty": MagicMock()}, "ap-southeast-3")

    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    check_kwargs = args[3]
    # alarm_names should NOT be injected for guardduty
    assert check_kwargs is None or "alarm_names" not in (check_kwargs or {})


def test_execute_parallel_request_check_params_override_alarm_names():
    executor = _make_executor()
    acct = _make_account("connect-prod", alarm_names=["db-alarm"])

    override_alarms = ["override-alarm"]
    with patch("src.app.services.check_executor._run_single_check") as mock_run:
        mock_run.return_value = {"status": "ok"}
        executor._execute_parallel(
            [acct],
            {"cloudwatch": MagicMock()},
            "ap-southeast-3",
            check_params={"alarm_names": override_alarms},
        )

    args, kwargs = mock_run.call_args
    check_kwargs = args[3]
    assert check_kwargs["alarm_names"] == override_alarms
