from unittest.mock import MagicMock, patch


def _make_account(profile_name: str):
    account = MagicMock()
    account.id = f"acct-{profile_name}"
    account.profile_name = profile_name
    account.display_name = profile_name.upper()
    account.is_active = True
    account.region = "ap-southeast-3"
    account.alarm_names = None
    account.config_extra = None
    return account


def _make_customer(customer_id: str, accounts: list):
    customer = MagicMock()
    customer.id = customer_id
    customer.display_name = customer_id.upper()
    customer.slack_enabled = False
    customer.slack_webhook_url = None
    customer.slack_channel = None
    customer.checks = []
    customer.accounts = accounts
    return customer


def test_execute_tui_mode_never_persists_to_db():
    from backend.domain.services.check_executor import CheckExecutor

    account = _make_account("prof-a")
    customer = _make_customer("cust-1", [account])

    customer_repo = MagicMock()
    customer_repo.get_customer.return_value = customer

    check_repo = MagicMock()

    executor = CheckExecutor(
        check_repo=check_repo,
        customer_repo=customer_repo,
        region="ap-southeast-3",
    )

    with patch("backend.domain.services.check_executor._run_single_check") as mock_run:
        mock_run.return_value = {
            "status": "ok",
            "summary": "ok",
            "_formatted_output": "ok",
        }
        result = executor.execute(
            customer_ids=["cust-1"],
            mode="single",
            check_name="health",
            send_slack=False,
            run_source="tui",
            persist_mode="none",
        )

    assert result["check_runs"] == []
    check_repo.create_check_run.assert_not_called()
    check_repo.add_result.assert_not_called()
    check_repo.finish_check_run.assert_not_called()
    check_repo.commit.assert_not_called()


def test_execute_api_mode_persists_to_db():
    from backend.domain.services.check_executor import CheckExecutor

    account = _make_account("prof-a")
    customer = _make_customer("cust-1", [account])

    customer_repo = MagicMock()
    customer_repo.get_customer.return_value = customer

    check_repo = MagicMock()
    check_run = MagicMock()
    check_run.id = "run-1"
    check_repo.create_check_run.return_value = check_run

    executor = CheckExecutor(
        check_repo=check_repo,
        customer_repo=customer_repo,
        region="ap-southeast-3",
    )

    with patch("backend.domain.services.check_executor._run_single_check") as mock_run:
        mock_run.return_value = {
            "status": "ok",
            "summary": "ok",
            "_formatted_output": "ok",
        }
        result = executor.execute(
            customer_ids=["cust-1"],
            mode="single",
            check_name="health",
            send_slack=False,
            run_source="api",
            persist_mode="normalized",
        )

    assert len(result["check_runs"]) == 1
    check_repo.create_check_run.assert_called_once()
    check_repo.add_result.assert_called()
    check_repo.finish_check_run.assert_called_once()
    check_repo.commit.assert_called_once()


def test_execute_api_mode_writes_normalized_finding_events_for_guardduty():
    from backend.domain.services.check_executor import CheckExecutor

    account = _make_account("prof-a")
    customer = _make_customer("cust-1", [account])

    customer_repo = MagicMock()
    customer_repo.get_customer.return_value = customer

    check_repo = MagicMock()
    check_run = MagicMock()
    check_run.id = "run-1"
    check_repo.create_check_run.return_value = check_run

    executor = CheckExecutor(
        check_repo=check_repo,
        customer_repo=customer_repo,
        region="ap-southeast-3",
    )

    with patch("backend.domain.services.check_executor._run_single_check") as mock_run:
        mock_run.return_value = {
            "status": "success",
            "findings": 1,
            "details": [
                {
                    "type": "Recon:EC2/PortProbeUnprotectedPort",
                    "severity": "HIGH",
                    "title": "Port probe detected",
                    "updated": "2026-03-19 13:00 WIB",
                }
            ],
            "_formatted_output": "ok",
        }
        executor.execute(
            customer_ids=["cust-1"],
            mode="single",
            check_name="guardduty",
            send_slack=False,
            run_source="api",
            persist_mode="normalized",
        )

    check_repo.add_finding_events.assert_called_once()
    args = check_repo.add_finding_events.call_args.kwargs
    assert args["check_run_id"] == "run-1"
    assert args["account_id"] == account.id
    assert len(args["events"]) == 1
    assert args["events"][0]["check_name"] == "guardduty"


def test_execute_tui_mode_does_not_write_normalized_finding_events():
    from backend.domain.services.check_executor import CheckExecutor

    account = _make_account("prof-a")
    customer = _make_customer("cust-1", [account])

    customer_repo = MagicMock()
    customer_repo.get_customer.return_value = customer

    check_repo = MagicMock()

    executor = CheckExecutor(
        check_repo=check_repo,
        customer_repo=customer_repo,
        region="ap-southeast-3",
    )

    with patch("backend.domain.services.check_executor._run_single_check") as mock_run:
        mock_run.return_value = {
            "status": "success",
            "findings": 1,
            "details": [
                {
                    "type": "Recon:EC2/PortProbeUnprotectedPort",
                    "severity": "HIGH",
                    "title": "Port probe detected",
                    "updated": "2026-03-19 13:00 WIB",
                }
            ],
            "_formatted_output": "ok",
        }
        executor.execute(
            customer_ids=["cust-1"],
            mode="single",
            check_name="guardduty",
            send_slack=False,
            run_source="tui",
            persist_mode="none",
        )

    check_repo.add_finding_events.assert_not_called()


def test_execute_api_mode_writes_normalized_finding_events_for_backup():
    from backend.domain.services.check_executor import CheckExecutor

    account = _make_account("prof-a")
    customer = _make_customer("cust-1", [account])

    customer_repo = MagicMock()
    customer_repo.get_customer.return_value = customer

    check_repo = MagicMock()
    check_run = MagicMock()
    check_run.id = "run-2"
    check_repo.create_check_run.return_value = check_run

    executor = CheckExecutor(
        check_repo=check_repo,
        customer_repo=customer_repo,
        region="ap-southeast-3",
    )

    with patch("backend.domain.services.check_executor._run_single_check") as mock_run:
        mock_run.return_value = {
            "status": "ATTENTION REQUIRED",
            "failed_jobs": 1,
            "expired_jobs": 1,
            "completed_jobs": 1,
            "job_details": [
                {
                    "job_id": "job-1",
                    "state": "FAILED",
                    "resource_label": "db-prod",
                    "reason": "Backup window missed",
                    "created_wib": "2026-03-19 02:10 WIB",
                },
                {
                    "job_id": "job-2",
                    "state": "EXPIRED",
                    "resource_label": "db-replica",
                    "reason": "Retention exceeded",
                    "created_wib": "2026-03-19 03:15 WIB",
                },
                {
                    "job_id": "job-3",
                    "state": "COMPLETED",
                    "resource_label": "db-archive",
                    "reason": "",
                    "created_wib": "2026-03-19 04:20 WIB",
                },
            ],
            "_formatted_output": "ok",
        }
        executor.execute(
            customer_ids=["cust-1"],
            mode="single",
            check_name="backup",
            send_slack=False,
            run_source="api",
            persist_mode="normalized",
        )

    check_repo.add_finding_events.assert_called_once()
    args = check_repo.add_finding_events.call_args.kwargs
    assert args["check_run_id"] == "run-2"
    assert args["account_id"] == account.id
    assert len(args["events"]) == 3
    assert args["events"][0]["check_name"] == "backup"


def test_execute_api_mode_writes_normalized_metric_samples_for_daily_arbel():
    from backend.domain.services.check_executor import CheckExecutor

    account = _make_account("prof-a")
    customer = _make_customer("cust-1", [account])

    customer_repo = MagicMock()
    customer_repo.get_customer.return_value = customer

    check_repo = MagicMock()
    check_run = MagicMock()
    check_run.id = "run-3"
    check_repo.create_check_run.return_value = check_run

    executor = CheckExecutor(
        check_repo=check_repo,
        customer_repo=customer_repo,
        region="ap-southeast-3",
    )

    with patch("backend.domain.services.check_executor._run_single_check") as mock_run:
        mock_run.return_value = {
            "status": "ATTENTION REQUIRED",
            "service_type": "rds",
            "instances": {
                "writer": {
                    "instance_id": "cis-prod-rds-instance",
                    "metrics": {
                        "CPUUtilization": {
                            "status": "warn",
                            "message": "CPU Utilization: 88% (di atas 75%)",
                        }
                    },
                }
            },
            "_formatted_output": "ok",
        }
        executor.execute(
            customer_ids=["cust-1"],
            mode="single",
            check_name="daily-arbel",
            send_slack=False,
            run_source="api",
            persist_mode="normalized",
        )

    check_repo.add_metric_samples.assert_called_once()
    args = check_repo.add_metric_samples.call_args.kwargs
    assert args["check_run_id"] == "run-3"
    assert args["account_id"] == account.id
    assert len(args["samples"]) == 1
    assert args["samples"][0]["check_name"] == "daily-arbel"


def test_execute_tui_mode_does_not_write_normalized_metric_samples():
    from backend.domain.services.check_executor import CheckExecutor

    account = _make_account("prof-a")
    customer = _make_customer("cust-1", [account])

    customer_repo = MagicMock()
    customer_repo.get_customer.return_value = customer

    check_repo = MagicMock()

    executor = CheckExecutor(
        check_repo=check_repo,
        customer_repo=customer_repo,
        region="ap-southeast-3",
    )

    with patch("backend.domain.services.check_executor._run_single_check") as mock_run:
        mock_run.return_value = {
            "status": "ATTENTION REQUIRED",
            "service_type": "rds",
            "instances": {
                "writer": {
                    "instance_id": "cis-prod-rds-instance",
                    "metrics": {
                        "CPUUtilization": {
                            "status": "warn",
                            "message": "CPU Utilization: 88% (di atas 75%)",
                        }
                    },
                }
            },
            "_formatted_output": "ok",
        }
        executor.execute(
            customer_ids=["cust-1"],
            mode="single",
            check_name="daily-arbel",
            send_slack=False,
            run_source="tui",
            persist_mode="none",
        )

    check_repo.add_metric_samples.assert_not_called()
