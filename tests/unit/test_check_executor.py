"""Tests for CheckExecutor per-account region and alarm_names injection."""

import time
import pytest
from unittest.mock import MagicMock, patch


def _make_executor(default_region="ap-southeast-3"):
    from backend.domain.services.check_executor import CheckExecutor

    executor = CheckExecutor(
        check_repo=MagicMock(),
        customer_repo=MagicMock(),
        region=default_region,
        timeout=30,
    )
    return executor


def _make_account(
    profile_name,
    region=None,
    alarm_names=None,
    config_extra=None,
    check_configs=None,
):
    acct = MagicMock()
    acct.profile_name = profile_name
    acct.region = region
    acct.alarm_names = alarm_names
    acct.config_extra = config_extra
    acct.check_configs = check_configs or []
    return acct


def test_execute_parallel_uses_account_region_when_set():
    executor = _make_executor(default_region="ap-southeast-3")
    acct = _make_account("bbi-prod", region="ap-southeast-1")

    with patch("backend.domain.services.check_executor._run_single_check") as mock_run:
        mock_run.return_value = {"status": "ok"}
        executor._execute_parallel(
            [acct], {"cloudwatch": MagicMock()}, "ap-southeast-3"
        )

    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    # _run_single_check(check_name, profile, region, check_kwargs)
    assert args[2] == "ap-southeast-1"


def test_execute_parallel_falls_back_to_effective_region_when_account_region_none():
    executor = _make_executor(default_region="ap-southeast-3")
    acct = _make_account("standard-prod", region=None)

    with patch("backend.domain.services.check_executor._run_single_check") as mock_run:
        mock_run.return_value = {"status": "ok"}
        executor._execute_parallel(
            [acct], {"cloudwatch": MagicMock()}, "ap-southeast-3"
        )

    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    assert args[2] == "ap-southeast-3"


def test_execute_parallel_injects_alarm_names_for_cloudwatch():
    executor = _make_executor()
    acct = _make_account("connect-prod", alarm_names=["alarm-a", "alarm-b"])

    with patch("backend.domain.services.check_executor._run_single_check") as mock_run:
        mock_run.return_value = {"status": "ok"}
        executor._execute_parallel(
            [acct], {"cloudwatch": MagicMock()}, "ap-southeast-3"
        )

    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    check_kwargs = args[3]
    assert check_kwargs is not None
    assert check_kwargs.get("alarm_names") == ["alarm-a", "alarm-b"]


def test_execute_parallel_does_not_inject_alarm_names_for_non_cloudwatch():
    executor = _make_executor()
    acct = _make_account("connect-prod", alarm_names=["alarm-a"])

    with patch("backend.domain.services.check_executor._run_single_check") as mock_run:
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
    with patch("backend.domain.services.check_executor._run_single_check") as mock_run:
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


def test_execute_parallel_merges_account_check_configs_for_target_check():
    executor = _make_executor()
    check_config_row = MagicMock()
    check_config_row.check_name = "daily-budget"
    check_config_row.config = {"budget_names": ["BudgetA"], "warn_percent": 85}
    acct = _make_account("finops-prod", check_configs=[check_config_row])

    with patch("backend.domain.services.check_executor._run_single_check") as mock_run:
        mock_run.return_value = {"status": "ok"}
        executor._execute_parallel(
            [acct], {"daily-budget": MagicMock()}, "ap-southeast-3"
        )

    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    check_kwargs = args[3]
    assert check_kwargs is not None
    assert check_kwargs["budget_names"] == ["BudgetA"]
    assert check_kwargs["warn_percent"] == 85


def test_execute_parallel_merges_account_check_configs_for_alarm_verification():
    executor = _make_executor()
    check_config_row = MagicMock()
    check_config_row.check_name = "alarm_verification"
    check_config_row.config = {
        "alarm_names": ["dc-dwh-olap-memory-above-70"],
        "min_duration_minutes": 15,
    }
    acct = _make_account("dwh", check_configs=[check_config_row])

    with patch("backend.domain.services.check_executor._run_single_check") as mock_run:
        mock_run.return_value = {"status": "ok"}
        executor._execute_parallel(
            [acct], {"alarm_verification": MagicMock()}, "ap-southeast-3"
        )

    args, _kwargs = mock_run.call_args
    check_kwargs = args[3]
    assert check_kwargs is not None
    assert check_kwargs["alarm_names"] == ["dc-dwh-olap-memory-above-70"]
    assert check_kwargs["min_duration_minutes"] == 15


def test_execute_parallel_merges_account_check_configs_for_backup():
    executor = _make_executor()
    check_config_row = MagicMock()
    check_config_row.check_name = "backup"
    check_config_row.config = {
        "vault_names": ["central-vault"],
        "monitor_rds_snapshots": False,
        "max_job_details": 10,
    }
    acct = _make_account("backup-hris", check_configs=[check_config_row])

    with patch("backend.domain.services.check_executor._run_single_check") as mock_run:
        mock_run.return_value = {"status": "ok"}
        executor._execute_parallel([acct], {"backup": MagicMock()}, "ap-southeast-3")

    args, _kwargs = mock_run.call_args
    check_kwargs = args[3]
    assert check_kwargs is not None
    assert check_kwargs["vault_names"] == ["central-vault"]
    assert check_kwargs["monitor_rds_snapshots"] is False
    assert check_kwargs["max_job_details"] == 10


def test_execute_parallel_merges_account_check_configs_for_aws_utilization():
    executor = _make_executor()
    check_config_row = MagicMock()
    check_config_row.check_name = "aws-utilization-3core"
    check_config_row.config = {
        "util_hours": 6,
        "thresholds": {"cpu_warning": 60, "cpu_critical": 80},
    }
    acct = _make_account("public-web", check_configs=[check_config_row])

    with patch("backend.domain.services.check_executor._run_single_check") as mock_run:
        mock_run.return_value = {"status": "ok"}
        executor._execute_parallel(
            [acct], {"aws-utilization-3core": MagicMock()}, "ap-southeast-3"
        )

    args, _kwargs = mock_run.call_args
    check_kwargs = args[3]
    assert check_kwargs is not None
    assert check_kwargs["util_hours"] == 6
    assert check_kwargs["thresholds"]["cpu_warning"] == 60
    assert check_kwargs["thresholds"]["cpu_critical"] == 80


def test_execute_parallel_times_out_stuck_checks():
    from backend.domain.services.check_executor import CheckExecutor

    executor = CheckExecutor(
        check_repo=MagicMock(),
        customer_repo=MagicMock(),
        region="ap-southeast-3",
        timeout=1,
    )
    acct = _make_account("connect-prod")

    def _slow_run(*_args, **_kwargs):
        time.sleep(1.2)
        return {"status": "ok"}

    with patch(
        "backend.domain.services.check_executor._run_single_check",
        side_effect=_slow_run,
    ):
        results = executor._execute_parallel(
            [acct], {"cloudwatch": MagicMock()}, "ap-southeast-3"
        )

    assert results[acct]["cloudwatch"]["status"] == "error"
    assert "timed out" in results[acct]["cloudwatch"]["error"]


def _make_customer(
    customer_id, display_name="Test", slack_enabled=False, accounts=None
):
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
    from backend.domain.services.check_executor import CheckExecutor

    cust1 = _make_customer(
        "cust-1", accounts=[_make_account("prof-a", region="ap-southeast-1")]
    )
    cust2 = _make_customer(
        "cust-2", accounts=[_make_account("prof-b", region="ap-southeast-1")]
    )

    customer_repo = MagicMock()
    customer_repo.get_customer.side_effect = lambda cid: {
        "cust-1": cust1,
        "cust-2": cust2,
    }[cid]

    check_repo = MagicMock()
    run1 = MagicMock()
    run1.id = "run-uuid-1"
    run2 = MagicMock()
    run2.id = "run-uuid-2"
    check_repo.create_check_run.side_effect = [run1, run2]

    executor = CheckExecutor(
        check_repo=check_repo, customer_repo=customer_repo, region="ap-southeast-3"
    )

    with patch("backend.domain.services.check_executor._run_single_check") as mock_run:
        mock_run.return_value = {"status": "ok", "_formatted_output": "ok"}
        result = executor.execute(
            customer_ids=["cust-1", "cust-2"], mode="all", send_slack=False
        )

    assert "check_runs" in result
    assert len(result["check_runs"]) == 2
    cids = {r["customer_id"] for r in result["check_runs"]}
    assert cids == {"cust-1", "cust-2"}
    assert result["customer_labels"] == {"cust-1": "Test", "cust-2": "Test"}


def test_execute_multi_customer_skips_unknown_customer():
    """execute() skips missing customers; all-missing raises ValueError."""
    from backend.domain.services.check_executor import CheckExecutor

    customer_repo = MagicMock()
    customer_repo.get_customer.return_value = None  # all unknown

    executor = CheckExecutor(
        check_repo=MagicMock(), customer_repo=customer_repo, region="ap-southeast-3"
    )

    with pytest.raises(ValueError, match="No valid customers"):
        executor.execute(
            customer_ids=["ghost-1", "ghost-2"], mode="all", send_slack=False
        )


def test_execute_multi_customer_skips_no_active_accounts():
    """execute() skips customers with zero active accounts."""
    from backend.domain.services.check_executor import CheckExecutor

    cust1 = _make_customer("cust-1", accounts=[])  # no accounts
    cust2 = _make_customer("cust-2", accounts=[_make_account("prof-b")])

    customer_repo = MagicMock()
    customer_repo.get_customer.side_effect = lambda cid: {
        "cust-1": cust1,
        "cust-2": cust2,
    }[cid]

    check_repo = MagicMock()
    run = MagicMock()
    run.id = "run-uuid-1"
    check_repo.create_check_run.return_value = run

    executor = CheckExecutor(
        check_repo=check_repo, customer_repo=customer_repo, region="ap-southeast-3"
    )

    with patch("backend.domain.services.check_executor._run_single_check") as mock_run:
        mock_run.return_value = {"status": "ok", "_formatted_output": "ok"}
        result = executor.execute(
            customer_ids=["cust-1", "cust-2"], mode="all", send_slack=False
        )

    # cust-1 skipped (no accounts), only cust-2 in check_runs
    assert len(result["check_runs"]) == 1
    assert result["check_runs"][0]["customer_id"] == "cust-2"


def test_execute_single_backup_returns_whatsapp_primary_output_and_backup_overview():
    from backend.domain.services.check_executor import CheckExecutor

    acct_ok = _make_account("connect-prod", region="ap-southeast-1")
    acct_fail = _make_account("ffi", region="ap-southeast-1")
    customer = _make_customer(
        "cust-1", display_name="Aryanoble", accounts=[acct_ok, acct_fail]
    )

    customer_repo = MagicMock()
    customer_repo.get_customer.return_value = customer

    check_repo = MagicMock()
    run = MagicMock()
    run.id = "run-uuid-1"
    check_repo.create_check_run.return_value = run

    executor = CheckExecutor(
        check_repo=check_repo,
        customer_repo=customer_repo,
        region="ap-southeast-3",
    )

    def _fake_run(check_name, profile, _region, _kwargs, _creds=None):
        base = {
            "status": "success",
            "total_jobs": 2,
            "completed_jobs": 2,
            "failed_jobs": 0,
            "expired_jobs": 0,
            "issues": [],
            "vaults": [],
            "_formatted_output": f"detail-{profile}",
        }
        if profile == "ffi":
            base["failed_jobs"] = 1
            base["completed_jobs"] = 1
            base["issues"] = ["1 failed job(s)"]
        return base

    with patch(
        "backend.domain.services.check_executor._run_single_check",
        side_effect=_fake_run,
    ):
        result = executor.execute(
            customer_ids=["cust-1"],
            mode="single",
            check_name="backup",
            send_slack=False,
        )

    assert result["consolidated_outputs"]["cust-1"]
    assert "Completed:" in result["consolidated_outputs"]["cust-1"]
    assert "Failed:" in result["consolidated_outputs"]["cust-1"]
    assert result["backup_overviews"]["cust-1"]["all_success"] is False
    assert result["backup_overviews"]["cust-1"]["problem_accounts_count"] == 1


def test_execute_single_daily_arbel_ec2_uses_account_name_keys_for_consolidated_outputs():
    from backend.domain.services.check_executor import CheckExecutor

    acct_hris = _make_account("HRIS", region="ap-southeast-3")
    acct_hris.id = "acc-hris"
    acct_hris.display_name = "Arbel HRIS"
    acct_hris.is_active = True

    acct_sfa = _make_account("sfa", region="ap-southeast-3")
    acct_sfa.id = "acc-sfa"
    acct_sfa.display_name = "Arbel SFA"
    acct_sfa.is_active = True

    customer = _make_customer(
        "cust-1", display_name="Aryanoble", accounts=[acct_hris, acct_sfa]
    )

    customer_repo = MagicMock()
    customer_repo.get_customer.return_value = customer

    check_repo = MagicMock()
    run = MagicMock()
    run.id = "run-uuid-1"
    check_repo.create_check_run.return_value = run

    executor = CheckExecutor(
        check_repo=check_repo,
        customer_repo=customer_repo,
        region="ap-southeast-3",
    )

    def _fake_run(*args, **_kwargs):
        _ = _kwargs
        check_name, profile = args[0], args[1]
        _ = check_name
        return {
            "status": "ok",
            "_formatted_output": f"report-{profile}",
        }

    with patch(
        "backend.domain.services.check_executor._run_single_check",
        side_effect=_fake_run,
    ):
        result = executor.execute(
            customer_ids=["cust-1"],
            mode="single",
            check_name="daily-arbel-ec2",
            send_slack=False,
        )

    outputs = result["consolidated_outputs"]
    assert outputs["Arbel HRIS"] == "report-HRIS"
    assert outputs["Arbel SFA"] == "report-sfa"
    assert all(not key.startswith("cust-1:") for key in outputs)


def test_ec2_utilization_uses_stored_instance_list():
    """instance_list kwarg skips _discover_regions and _list_instances."""
    from backend.checks.generic.aws_utilization_3core import AWSUtilization3CoreChecker
    from unittest.mock import patch, MagicMock

    stored_instances = [
        {
            "instance_id": "i-abc123",
            "name": "my-server",
            "os_type": "linux",
            "instance_type": "t3.small",
            "region": "ap-southeast-3",
        }
    ]

    checker = AWSUtilization3CoreChecker(instance_list=stored_instances)

    with patch.object(checker, "_discover_regions") as mock_discover, \
         patch.object(checker, "_list_instances") as mock_list, \
         patch.object(checker, "_get_session") as mock_session, \
         patch.object(checker, "_collect_instance_metrics") as mock_collect:

        mock_collect.return_value = {**stored_instances[0], "cpu_avg_12h": 10.0,
            "cpu_peak_12h": 15.0, "cpu_peak_at_12h": None, "memory_avg_12h": None,
            "memory_peak_12h": None, "memory_peak_at_12h": None, "memory_metric": None,
            "memory_note": None, "disk_free_min_percent": None, "disk_note": None,
            "status": "NORMAL"}
        mock_session.return_value = MagicMock()

        result = checker.check("test-profile", "123456789012")

    mock_discover.assert_not_called()
    mock_list.assert_not_called()
    assert result["status"] == "success"
    assert len(result["instances"]) == 1
    assert result["instances"][0]["instance_id"] == "i-abc123"


def test_executor_injects_instance_list_from_discovery():
    """_execute_parallel injects instance_list into ec2_utilization kwargs from _discovery."""
    executor = _make_executor()

    discovery_data = {
        "ec2_instances": [
            {
                "instance_id": "i-aaa111",
                "name": "prod-server",
                "instance_type": "t3.medium",
                "region": "ap-southeast-3",
                "platform": "",
            },
            {
                "instance_id": "i-bbb222",
                "name": "win-server",
                "instance_type": "t3.large",
                "region": "ap-southeast-3",
                "platform": "windows",
            },
        ]
    }
    acct = _make_account("prod-profile", config_extra={"_discovery": discovery_data})

    captured_kwargs = {}

    def capture(*args, **kwargs):
        # _run_single_check(check_name, profile, region, check_kwargs, injected_creds)
        captured_kwargs[args[0]] = args[3]
        return {"status": "ok"}

    with patch("backend.domain.services.check_executor._run_single_check", side_effect=capture):
        executor._execute_parallel(
            [acct], {"ec2_utilization": MagicMock()}, "ap-southeast-3"
        )

    assert "ec2_utilization" in captured_kwargs
    injected = captured_kwargs["ec2_utilization"]
    assert injected is not None
    instance_list = injected["instance_list"]
    assert len(instance_list) == 2
    linux = next(i for i in instance_list if i["instance_id"] == "i-aaa111")
    win = next(i for i in instance_list if i["instance_id"] == "i-bbb222")
    assert linux["os_type"] == "linux"
    assert win["os_type"] == "windows"
