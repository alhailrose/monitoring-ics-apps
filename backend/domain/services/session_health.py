"""AWS SSO session health check service.

Checks credential validity for all customer accounts,
detects expired sessions, and notifies via Slack + logging.
"""

from __future__ import annotations

import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from configparser import ConfigParser
from dataclasses import dataclass, field
from pathlib import Path

from backend.infra.cloud.aws.clients import get_session as get_aws_session
from backend.infra.notifications.slack.notifier import send_to_webhook

logger = logging.getLogger(__name__)

AWS_CONFIG_PATH = Path.home() / ".aws" / "config"


@dataclass
class ProfileStatus:
    profile_name: str
    account_id: str | None = None
    display_name: str = ""
    status: str = "unknown"  # ok, expired, error, no_config
    error: str = ""
    sso_session: str = ""
    login_command: str = ""


@dataclass
class SessionHealthReport:
    total_profiles: int = 0
    ok: int = 0
    expired: int = 0
    error: int = 0
    profiles: list[ProfileStatus] = field(default_factory=list)
    sso_sessions: dict[str, dict] = field(default_factory=dict)


def _get_sso_session_for_profile(
    profile_name: str,
    aws_config_path: Path | None = None,
) -> str | None:
    """Read ~/.aws/config to find the sso_session for a profile."""
    config_path = aws_config_path or AWS_CONFIG_PATH
    if not config_path.exists():
        return None
    parser = ConfigParser()
    parser.read(str(config_path))

    # Try "profile <name>" section (standard aws config format)
    section = f"profile {profile_name}"
    if section not in parser:
        # Try just the name (for default or non-standard)
        section = profile_name
    if section not in parser:
        return None

    return parser.get(section, "sso_session", fallback=None)


def _check_profile_health(
    profile_name: str,
    aws_config_path: Path | None = None,
    aws_config_file: str | None = None,
) -> ProfileStatus:
    """Check if a single profile's credentials are valid via STS."""
    result = ProfileStatus(profile_name=profile_name)
    result.sso_session = (
        _get_sso_session_for_profile(profile_name, aws_config_path) or ""
    )

    if result.sso_session:
        result.login_command = f"aws sso login --sso-session {result.sso_session}"
    else:
        result.login_command = f"aws sso login --profile {profile_name}"

    try:
        session = get_aws_session(
            profile_name=profile_name,
            aws_config_file=aws_config_file,
        )
        sts = session.client("sts")
        identity = sts.get_caller_identity()
        result.account_id = identity.get("Account")
        result.status = "ok"
    except Exception as exc:
        msg = str(exc).lower()
        if any(
            hint in msg for hint in ("expired", "token", "sso", "unable to load sso")
        ):
            result.status = "expired"
            result.error = f"SSO session expired. Run: {result.login_command}"
        elif "no credentials" in msg or "profile" in msg:
            result.status = "no_config"
            result.error = str(exc)
        else:
            result.status = "error"
            result.error = str(exc)

    return result


class SessionHealthService:
    """Check and report on AWS SSO session health for all customer accounts."""

    def __init__(
        self,
        customer_repo,
        max_workers: int = 10,
        aws_config_file: str | None = None,
    ):
        self.customer_repo = customer_repo
        self.max_workers = max_workers
        self.aws_config_file = aws_config_file
        self.aws_config_path = (
            Path(aws_config_file) if aws_config_file else AWS_CONFIG_PATH
        )

    def check_all(self, customer_id: str | None = None) -> SessionHealthReport:
        """Check session health for all accounts (or one customer's accounts).

        Args:
            customer_id: If provided, only check this customer's accounts.
                         If None, check all customers.

        Returns:
            SessionHealthReport with per-profile status
        """
        if customer_id:
            customers = [self.customer_repo.get_customer(customer_id)]
            customers = [c for c in customers if c is not None]
        else:
            customers = self.customer_repo.list_customers()

        # Collect all profiles to check
        profiles_to_check = []
        profile_display = {}
        for customer in customers:
            for account in customer.accounts:
                if account.is_active:
                    profiles_to_check.append(account.profile_name)
                    profile_display[account.profile_name] = (
                        account.display_name,
                        customer.display_name,
                    )

        # Deduplicate (same profile might be in multiple customers)
        unique_profiles = list(dict.fromkeys(profiles_to_check))

        # Check in parallel
        report = SessionHealthReport(total_profiles=len(unique_profiles))
        results = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    _check_profile_health,
                    p,
                    self.aws_config_path,
                    self.aws_config_file,
                ): p
                for p in unique_profiles
            }
            for future in as_completed(futures):
                profile = futures[future]
                try:
                    status = future.result()
                except Exception as exc:
                    status = ProfileStatus(
                        profile_name=profile,
                        status="error",
                        error=str(exc),
                    )

                # Attach display name
                if profile in profile_display:
                    status.display_name = profile_display[profile][0]

                results[profile] = status

        # Build report
        sso_sessions = {}
        for profile in unique_profiles:
            status = results[profile]
            report.profiles.append(status)

            if status.status == "ok":
                report.ok += 1
            elif status.status == "expired":
                report.expired += 1
                logger.warning(
                    f"SSO expired: {profile} ({status.display_name}). "
                    f"Run: {status.login_command}"
                )
            else:
                report.error += 1

            # Group by SSO session
            if status.sso_session:
                if status.sso_session not in sso_sessions:
                    sso_sessions[status.sso_session] = {
                        "session_name": status.sso_session,
                        "login_command": f"aws sso login --sso-session {status.sso_session}",
                        "status": "ok",
                        "profiles_ok": [],
                        "profiles_expired": [],
                        "profiles_error": [],
                    }
                sess = sso_sessions[status.sso_session]
                if status.status == "ok":
                    sess["profiles_ok"].append(profile)
                elif status.status == "expired":
                    sess["profiles_expired"].append(profile)
                    sess["status"] = "expired"
                else:
                    sess["profiles_error"].append(profile)
                    if sess["status"] != "expired":
                        sess["status"] = "error"

        report.sso_sessions = sso_sessions
        return report

    def check_and_notify_with_customer(
        self,
        customer_id: str | None = None,
    ) -> SessionHealthReport:
        """Check session health and notify via customer's configured Slack webhook.

        Resolves the customer's slack_webhook_url and slack_channel from the
        database (only when customer_id is provided and slack_enabled is True)
        before delegating to check_and_notify().

        Args:
            customer_id: Optional customer filter. If provided, uses that
                         customer's Slack config for notification.

        Returns:
            SessionHealthReport
        """
        slack_webhook_url = None
        slack_channel = None

        if customer_id:
            customer = self.customer_repo.get_customer(customer_id)
            if customer and customer.slack_enabled and customer.slack_webhook_url:
                slack_webhook_url = customer.slack_webhook_url
                slack_channel = customer.slack_channel

        return self.check_and_notify(
            customer_id=customer_id,
            slack_webhook_url=slack_webhook_url,
            slack_channel=slack_channel,
        )

    def check_and_notify(
        self,
        customer_id: str | None = None,
        slack_webhook_url: str | None = None,
        slack_channel: str | None = None,
    ) -> SessionHealthReport:
        """Check session health and send notification if any sessions are expired.

        Args:
            customer_id: Optional customer filter
            slack_webhook_url: Webhook to send notification to
            slack_channel: Optional channel override

        Returns:
            SessionHealthReport
        """
        report = self.check_all(customer_id)

        if report.expired == 0 and report.error == 0:
            logger.info(
                f"Session health OK: {report.ok}/{report.total_profiles} profiles healthy"
            )
            return report

        # Build notification message
        lines = [
            "AWS SSO Session Health Alert",
            f"Status: {report.expired} expired, {report.error} error, {report.ok} ok "
            f"(out of {report.total_profiles})",
            "",
        ]

        # Group by SSO session for actionable output
        for sess_name, sess_info in report.sso_sessions.items():
            if sess_info["status"] != "ok":
                lines.append(
                    f"SSO Session: {sess_name} [{sess_info['status'].upper()}]"
                )
                lines.append(f"  Fix: {sess_info['login_command']}")
                if sess_info["profiles_expired"]:
                    lines.append(
                        f"  Expired profiles: {', '.join(sess_info['profiles_expired'])}"
                    )
                if sess_info["profiles_error"]:
                    lines.append(
                        f"  Error profiles: {', '.join(sess_info['profiles_error'])}"
                    )
                lines.append("")

        # Log the full message
        message = "\n".join(lines)
        logger.warning(f"SSO Session Health Alert:\n{message}")

        # Send to Slack if webhook provided
        if slack_webhook_url:
            sent, reason = send_to_webhook(
                slack_webhook_url, message, channel=slack_channel
            )
            if sent:
                logger.info("Session health alert sent to Slack")
            else:
                logger.error(f"Failed to send session health alert to Slack: {reason}")

        return report

    @staticmethod
    def serialize_report(report: SessionHealthReport) -> dict:
        """Serialize report for API response."""
        return {
            "total_profiles": report.total_profiles,
            "ok": report.ok,
            "expired": report.expired,
            "error": report.error,
            "profiles": [
                {
                    "profile_name": p.profile_name,
                    "account_id": p.account_id,
                    "display_name": p.display_name,
                    "status": p.status,
                    "error": p.error,
                    "sso_session": p.sso_session,
                    "login_command": p.login_command,
                }
                for p in report.profiles
            ],
            "sso_sessions": report.sso_sessions,
        }
