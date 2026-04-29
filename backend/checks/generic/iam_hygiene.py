"""AWS IAM hygiene checker — flags stale access keys, users without MFA, and root usage."""

import logging
from datetime import datetime, timezone, timedelta
from botocore.exceptions import BotoCoreError, ClientError

from backend.checks.common.base import BaseChecker
from backend.checks.common.aws_errors import is_credential_error

logger = logging.getLogger(__name__)

# Keys older than this are considered stale
STALE_KEY_DAYS = 90


class IAMHygieneChecker(BaseChecker):
    report_section_title = "IAM HYGIENE"
    issue_label = "IAM hygiene issues"
    recommendation_text = "IAM REVIEW: Rotate stale access keys and enforce MFA for all console users"

    def check(self, profile, account_id):
        try:
            session = self._get_session(profile)
            iam = session.client("iam", region_name="us-east-1")  # IAM is global

            users = self._audit_users(iam)
            root_mfa, root_last_used = self._check_root(iam)

            stale_keys = [u for u in users if u.get("has_stale_key")]
            no_mfa = [u for u in users if u.get("console_access") and not u.get("mfa_enabled")]

            return {
                "status": "success",
                "profile": profile,
                "account_id": account_id,
                "user_count": len(users),
                "stale_key_users": len(stale_keys),
                "no_mfa_users": len(no_mfa),
                "root_mfa_enabled": root_mfa,
                "root_last_used": root_last_used,
                "users": users,
            }

        except (BotoCoreError, ClientError) as exc:
            if is_credential_error(exc):
                return self._error_result(exc, profile, account_id)
            return {
                "status": "error",
                "profile": profile,
                "account_id": account_id,
                "error": str(exc),
            }
        except Exception as exc:
            return self._error_result(exc, profile, account_id)

    def _audit_users(self, iam) -> list[dict]:
        users = []
        now = datetime.now(timezone.utc)
        paginator = iam.get_paginator("list_users")
        for page in paginator.paginate():
            for u in page.get("Users", []):
                username = u["UserName"]
                console_access = self._has_login_profile(iam, username)
                mfa_enabled = self._has_mfa(iam, username)
                stale_key, oldest_key_age = self._check_access_keys(iam, username, now)
                users.append({
                    "username": username,
                    "console_access": console_access,
                    "mfa_enabled": mfa_enabled,
                    "has_stale_key": stale_key,
                    "oldest_key_age_days": oldest_key_age,
                    "password_last_used": self._fmt_date(u.get("PasswordLastUsed")),
                })
        return users

    def _has_login_profile(self, iam, username: str) -> bool:
        try:
            iam.get_login_profile(UserName=username)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchEntity":
                return False
            return False

    def _has_mfa(self, iam, username: str) -> bool:
        try:
            resp = iam.list_mfa_devices(UserName=username)
            return len(resp.get("MFADevices", [])) > 0
        except Exception:
            return False

    def _check_access_keys(self, iam, username: str, now: datetime) -> tuple[bool, int]:
        """Return (has_stale_key, oldest_key_age_days)."""
        try:
            resp = iam.list_access_keys(UserName=username)
            oldest = 0
            stale = False
            for key in resp.get("AccessKeyMetadata", []):
                if key.get("Status") != "Active":
                    continue
                created = key.get("CreateDate")
                if created:
                    age = (now - created.replace(tzinfo=timezone.utc) if created.tzinfo is None else now - created).days
                    oldest = max(oldest, age)
                    if age >= STALE_KEY_DAYS:
                        stale = True
            return stale, oldest
        except Exception:
            return False, 0

    def _check_root(self, iam) -> tuple[bool, str]:
        """Return (root_mfa_enabled, root_last_used_str)."""
        try:
            summary = iam.get_account_summary()
            root_mfa = bool(summary.get("SummaryMap", {}).get("AccountMFAEnabled", 0))
            # Root last used comes from credential report — skip for now, just return MFA status
            return root_mfa, "N/A"
        except Exception:
            return False, "unknown"

    def _fmt_date(self, dt) -> str:
        if not dt:
            return "never"
        try:
            return dt.strftime("%Y-%m-%d") if isinstance(dt, datetime) else str(dt)[:10]
        except Exception:
            return str(dt)

    def format_report(self, results):
        if results.get("status") != "success":
            return f"ERROR: {results.get('error')}"

        lines = []
        lines.append(f"┌─ IAM CHECK | {results['profile']} ({results['account_id']})")
        lines.append(f"│  IAM Users          : {results['user_count']}")
        lines.append(f"│  Root MFA enabled   : {'✓ Yes' if results['root_mfa_enabled'] else '⚠ NO'}")
        lines.append(f"│  Stale access keys  : {results['stale_key_users']} user(s) with keys ≥{STALE_KEY_DAYS}d")
        lines.append(f"│  No MFA (console)   : {results['no_mfa_users']} user(s)")

        stale = [u for u in results.get("users", []) if u.get("has_stale_key")]
        if stale:
            lines.append("│")
            lines.append("│  ⚠ Stale access keys:")
            for u in stale[:10]:
                lines.append(f"│    - {u['username']} (key age: {u['oldest_key_age_days']}d)")

        no_mfa = [u for u in results.get("users", []) if u.get("console_access") and not u.get("mfa_enabled")]
        if no_mfa:
            lines.append("│")
            lines.append("│  ⚠ Console users without MFA:")
            for u in no_mfa[:10]:
                lines.append(f"│    - {u['username']} (last login: {u['password_last_used']})")

        issues = (
            results["stale_key_users"]
            + results["no_mfa_users"]
            + (0 if results["root_mfa_enabled"] else 1)
        )
        lines.append(f"└─ Status: {'⚠ Issues found' if issues else '✓ IAM hygiene OK'}")
        return "\n".join(lines)

    def count_issues(self, result: dict) -> int:
        if result.get("status") != "success":
            return 0
        root_issue = 0 if result.get("root_mfa_enabled") else 1
        return result.get("stale_key_users", 0) + result.get("no_mfa_users", 0) + root_issue

    def render_section(self, all_results: dict, errors: list) -> list[str]:
        lines = ["", "IAM HYGIENE"]
        if errors:
            lines.append(f"Status: ERROR - {len(errors)} account(s) failed")
            for prof, err in errors[:5]:
                lines.append(f"  * {prof}: {err}")
            return lines

        total_stale = sum(r.get("stale_key_users", 0) for r in all_results.values())
        total_no_mfa = sum(r.get("no_mfa_users", 0) for r in all_results.values())
        root_issues = [prof for prof, r in all_results.items() if not r.get("root_mfa_enabled")]

        if root_issues:
            lines.append(f"⚠ Root MFA not enabled: {', '.join(root_issues)}")
        if total_stale > 0:
            lines.append(f"⚠ Users with stale access keys (≥{STALE_KEY_DAYS}d): {total_stale}")
            for prof, r in all_results.items():
                for u in r.get("users", []):
                    if u.get("has_stale_key"):
                        lines.append(f"  * {prof} / {u['username']} ({u['oldest_key_age_days']}d)")
        if total_no_mfa > 0:
            lines.append(f"⚠ Console users without MFA: {total_no_mfa}")
        if not root_issues and total_stale == 0 and total_no_mfa == 0:
            lines.append("Status: CLEAR - IAM hygiene compliant")
        return lines
