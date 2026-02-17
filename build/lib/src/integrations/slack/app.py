"""Slack adapter facade for centralized runner commands."""

from src.integrations.slack.commands import dispatch_slack_command


class SlackCommandService:
    def __init__(self, submit_job, get_job_status):
        self.submit_job = submit_job
        self.get_job_status = get_job_status

    def handle_text(self, text, requested_by=None):
        return dispatch_slack_command(
            text,
            submit_job=self.submit_job,
            get_job_status=self.get_job_status,
            requested_by=requested_by,
        )
