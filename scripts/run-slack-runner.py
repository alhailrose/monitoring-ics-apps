#!/usr/bin/env python3
"""Minimal local entrypoint for Slack-command-style runner flow.

This is a development helper script to validate parser + job plumbing.
"""

from pathlib import Path

from monitoring_hub.integrations.slack.app import SlackCommandService
from monitoring_hub.runner.job_store import JobStore


def main():
    store = JobStore(Path(".runtime/jobs.db"))

    def submit_job(kind, payload, requested_by=None):
        rec = store.create_job(kind, payload, requested_by=requested_by)
        if rec is None:
            raise RuntimeError("failed to create job")
        return rec.job_id

    def get_job_status(job_id):
        rec = store.get_job(job_id)
        if not rec:
            return None
        return {"job_id": rec.job_id, "status": rec.status}

    service = SlackCommandService(submit_job=submit_job, get_job_status=get_job_status)

    print("Type Slack-like command, example: /monitor run arbel budget")
    text = input("> ").strip()
    print(service.handle_text(text, requested_by="local-cli"))


if __name__ == "__main__":
    main()
