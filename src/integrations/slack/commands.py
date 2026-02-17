"""Slack command parsing and dispatch helpers."""


def parse_slack_command(text):
    tokens = (text or "").strip().split()
    if not tokens:
        raise ValueError("empty command")

    if len(tokens) >= 3 and tokens[0] == "/monitor" and tokens[1] == "status":
        return {"action": "status", "job_id": tokens[2]}

    if len(tokens) >= 4 and tokens[:4] == ["/monitor", "run", "arbel", "budget"]:
        return {"action": "run", "job_kind": "arbel-budget", "payload": {}}

    if len(tokens) >= 4 and tokens[:4] == ["/monitor", "run", "arbel", "rds"]:
        payload = {"window": "3h"}
        if "--window" in tokens:
            idx = tokens.index("--window")
            if idx + 1 < len(tokens):
                payload["window"] = tokens[idx + 1]
        return {"action": "run", "job_kind": "arbel-rds", "payload": payload}

    raise ValueError(f"unsupported command: {text}")


def dispatch_slack_command(text, submit_job, get_job_status, requested_by=None):
    parsed = parse_slack_command(text)

    if parsed["action"] == "run":
        job_id = submit_job(
            parsed["job_kind"],
            parsed.get("payload", {}),
            requested_by=requested_by,
        )
        return f"Job diterima: {job_id}"

    status = get_job_status(parsed["job_id"])
    if not status:
        return f"Job tidak ditemukan: {parsed['job_id']}"

    return f"Job {status['job_id']} status: {status['status']}"
