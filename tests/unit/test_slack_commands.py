from src.integrations.slack.commands import (
    dispatch_slack_command,
    parse_slack_command,
)


def test_parse_run_arbel_rds_with_window():
    parsed = parse_slack_command("/monitor run arbel rds --window 12h")

    assert parsed["action"] == "run"
    assert parsed["job_kind"] == "arbel-rds"
    assert parsed["payload"]["window"] == "12h"


def test_parse_run_arbel_budget():
    parsed = parse_slack_command("/monitor run arbel budget")

    assert parsed["action"] == "run"
    assert parsed["job_kind"] == "arbel-budget"


def test_parse_status_command():
    parsed = parse_slack_command("/monitor status job-123")

    assert parsed == {"action": "status", "job_id": "job-123"}


def test_dispatch_run_command_uses_submit_job():
    calls = {}

    def _submit(kind, payload, requested_by=None):
        calls["kind"] = kind
        calls["payload"] = payload
        calls["requested_by"] = requested_by
        return "job-abc"

    reply = dispatch_slack_command(
        "/monitor run arbel budget",
        submit_job=_submit,
        get_job_status=lambda _job_id: None,
        requested_by="slack:user",
    )

    assert calls["kind"] == "arbel-budget"
    assert calls["requested_by"] == "slack:user"
    assert "job-abc" in reply


def test_dispatch_status_command_uses_get_job_status():
    reply = dispatch_slack_command(
        "/monitor status job-xyz",
        submit_job=lambda *_args, **_kwargs: "",
        get_job_status=lambda job_id: {"job_id": job_id, "status": "running"},
        requested_by="slack:user",
    )

    assert "job-xyz" in reply
    assert "running" in reply
