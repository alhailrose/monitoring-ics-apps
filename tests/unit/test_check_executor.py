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


def _make_customer(customer_id, display_name="Test", slack_enabled=False, accounts=None):
    customer = MagicMock()
    customer.id = customer_id
    customer.display_name = display_name
    customer.slack_enabled = slack_enabled
    customer.slack_webhook_url = None
    customer.slack_channel = None
    customer.checks = []
    customer.accounts = accounts or []
    return customer


def test_execute_multi_customer_returns_check_runs_list():
    """execute() with two customer_ids returns two entries in check_runs."""
    from src.app.services.check_executor import CheckExecutor

    cust1 = _make_customer("cust-1", accounts=[_make_account("prof-a", region="ap-southeast-1")])
    cust2 = _make_customer("cust-2", accounts=[_make_account("prof-b", region="ap-southeast-1")])

    customer_repo = MagicMock()
    customer_repo.get_customer.side_effect = lambda cid: {"cust-1": cust1, "cust-2": cust2}[cid]

    check_repo = MagicMock()
    run1 = MagicMock(); run1.id = "run-uuid-1"
    run2 = MagicMock(); run2.id = "run-uuid-2"
    check_repo.create_check_run.side_effect = [run1, run2]

    executor = CheckExecutor(check_repo=check_repo, customer_repo=customer_repo, region="ap-southeast-3")

    with patch("src.app.services.check_executor._run_single_check") as mock_run:
        mock_run.return_value = {"status": "ok", "_formatted_output": "ok"}
        result = executor.execute(customer_ids=["cust-1", "cust-2"], mode="all", send_slack=False)

    assert "check_runs" in result
    assert len(result["check_runs"]) == 2
    cids = {r["customer_id"] for r in result["check_runs"]}
    assert cids == {"cust-1", "cust-2"}


def test_execute_multi_customer_skips_unknown_customer():
    """execute() skips missing customers; all-missing raises ValueError."""
    from src.app.services.check_executor import CheckExecutor

    customer_repo = MagicMock()
    customer_repo.get_customer.return_value = None  # all unknown

    executor = CheckExecutor(check_repo=MagicMock(), customer_repo=customer_repo, region="ap-southeast-3")

    with pytest.raises(ValueError, match="No valid customers"):
        executor.execute(customer_ids=["ghost-1", "ghost-2"], mode="all", send_slack=False)


def test_execute_multi_customer_skips_no_active_accounts():
    """execute() skips customers with zero active accounts."""
    from src.app.services.check_executor import CheckExecutor

    cust1 = _make_customer("cust-1", accounts=[])  # no accounts
    cust2 = _make_customer("cust-2", accounts=[_make_account("prof-b")])

    customer_repo = MagicMock()
    customer_repo.get_customer.side_effect = lambda cid: {"cust-1": cust1, "cust-2": cust2}[cid]

    check_repo = MagicMock()
    run = MagicMock(); run.id = "run-uuid-1"
    check_repo.create_check_run.return_value = run

    executor = CheckExecutor(check_repo=check_repo, customer_repo=customer_repo, region="ap-southeast-3")

    with patch("src.app.services.check_executor._run_single_check") as mock_run:
        mock_run.return_value = {"status": "ok", "_formatted_output": "ok"}
        result = executor.execute(customer_ids=["cust-1", "cust-2"], mode="all", send_slack=False)

    # cust-1 skipped (no accounts), only cust-2 in check_runs
    assert len(result["check_runs"]) == 1
    assert result["check_runs"][0]["customer_id"] == "cust-2"
