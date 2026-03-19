"""Synchronous check execution service.

Replaces the old async job queue with direct execution,
mirroring TUI functionality for the web interface.

Supports three modes:
- single: Run one check on selected accounts, return detailed per-account output
- all: Run customer-configured checks, return consolidated report
- arbel: Fixed Aryanoble preset, return consolidated report with WhatsApp messages
"""

from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ALL_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, date, timedelta, timezone
from typing import Optional

from backend.domain.runtime.config import (
    AVAILABLE_CHECKS,
    ALL_MODE_CHECKS,
    DEFAULT_WORKERS,
)
from backend.domain.runtime.utils import get_account_id as get_account_id_from_profile
from backend.domain.runtime.reports import (
    build_whatsapp_backup,
    build_whatsapp_rds,
    summarize_backup_whatsapp,
)
from backend.domain.services.finding_events_mapper import map_check_findings
from backend.domain.services.metric_samples_mapper import map_check_metric_samples
from src.checks.common.aws_errors import (
    is_credential_error,
    friendly_credential_message,
)
from backend.infra.notifications.slack.notifier import send_to_webhook

logger = logging.getLogger(__name__)

# Arbel-specific checks (fixed preset for Aryanoble)
ARBEL_CHECKS = [
    "cost",
    "guardduty",
    "cloudwatch",
    "notifications",
    "backup",
    "daily-arbel",
]


def _json_safe(obj):
    """Recursively convert non-serializable objects to strings."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(item) for item in obj]
    if isinstance(obj, set):
        return [_json_safe(item) for item in obj]
    try:
        json.dumps(obj)
        return obj
    except (TypeError, ValueError):
        return str(obj)


def _normalize_status(raw_result: dict, check_name: str) -> str:
    """Extract a normalized status from raw check result."""
    status = raw_result.get("status", "error")
    if isinstance(status, str):
        upper = status.upper()
        if upper in ("OK", "WARN", "ERROR", "ALARM", "NO_DATA"):
            return upper
    if check_name == "guardduty":
        findings = raw_result.get("findings", [])
        if isinstance(findings, list) and len(findings) > 0:
            return "WARN"
        return "OK"
    if check_name == "cost":
        anomalies = raw_result.get("anomalies", [])
        if isinstance(anomalies, list) and len(anomalies) > 0:
            return "ALARM"
        return "OK"
    if check_name == "cloudwatch":
        alarm_count = raw_result.get("in_alarm", 0)
        if alarm_count and int(alarm_count) > 0:
            return "ALARM"
        return "OK"
    return "ERROR" if status == "error" else "OK"


def _build_summary(raw_result: dict, check_name: str) -> str:
    """Build a short summary string from raw check result."""
    if raw_result.get("status") == "error":
        return f"Error: {raw_result.get('error', 'Unknown')}"
    if check_name == "guardduty":
        findings = raw_result.get("findings", [])
        count = len(findings) if isinstance(findings, list) else 0
        if count > 0:
            return f"{count} finding(s) detected"
        return "No findings"
    if check_name == "cost":
        anomalies = raw_result.get("anomalies", [])
        count = len(anomalies) if isinstance(anomalies, list) else 0
        if count > 0:
            return f"{count} cost anomaly(ies)"
        return "No anomalies"
    if check_name == "cloudwatch":
        in_alarm = raw_result.get("in_alarm", 0)
        total = raw_result.get("total_alarms", 0)
        return f"{in_alarm}/{total} alarms in ALARM state"
    if check_name == "notifications":
        count = raw_result.get("notification_count", 0)
        return f"{count} notification(s)"
    return raw_result.get("summary", "Check completed")


def _run_single_check(
    check_name: str,
    profile: str,
    region: str,
    check_kwargs: Optional[dict] = None,
) -> dict:
    """Run one check on one profile, return raw result."""
    checker_class = AVAILABLE_CHECKS.get(check_name)
    if checker_class is None:
        return {"status": "error", "error": f"Unknown check: {check_name}"}

    account_id = get_account_id_from_profile(profile)
    checker = checker_class(region=region, **(check_kwargs or {}))

    try:
        result = checker.check(profile, account_id)
        try:
            result["_formatted_output"] = checker.format_report(result)
        except Exception:
            result["_formatted_output"] = str(result)
        # Attach checker instance for consolidated report building
        result["_checker_instance"] = checker
        return result
    except Exception as exc:
        if is_credential_error(exc):
            return {
                "status": "error",
                "error": friendly_credential_message(exc, profile),
                "is_credential_error": True,
            }
        return {"status": "error", "error": str(exc)}


def _build_consolidated_report(
    profiles: list[str],
    all_results: dict[str, dict[str, dict]],
    checks: list[str],
    checkers: dict,
    check_errors: list[tuple],
    clean_accounts: list[str],
    errors_by_check: dict[str, list],
    region: str,
    group_name: str | None = None,
) -> str:
    """Build consolidated daily monitoring report text.

    Mirrors TUI _print_consolidated_report() from runners.py but returns
    the text instead of printing it.

    Args:
        profiles: List of AWS profile names
        all_results: {profile: {check_name: result_dict}}
        checks: List of check names that were run
        checkers: {check_name: checker_instance} — instantiated checkers
        check_errors: [(profile, check_name, error_msg)]
        clean_accounts: Profiles with zero issues
        errors_by_check: {check_name: [(profile, error_msg)]}
        region: AWS region
        group_name: Customer/group name for header

    Returns:
        Full report text string
    """
    now = datetime.now()
    date_str = now.strftime("%B %d, %Y")
    time_str = now.strftime("%H:%M WIB")

    include_backup_rds = "backup" in checks or "daily-arbel" in checks

    lines = []

    # Header
    if include_backup_rds:
        lines.append("=" * 70)
        if group_name:
            lines.append(f"DAILY MONITORING REPORT - {group_name.upper()} GROUP")
        else:
            lines.append("DAILY MONITORING REPORT")
        lines.append("=" * 70)
        lines.append(f"Date: {date_str}")
        lines.append(f"Time: {time_str}")
        lines.append(f"Scope: {len(profiles)} AWS Accounts | Region: {region}")
        lines.append("")
        lines.append("-" * 70)
    else:
        lines.append("DAILY MONITORING REPORT")
        lines.append(f"Date: {date_str}")
        lines.append(f"Scope: {len(profiles)} AWS Accounts | Region: {region}")
        lines.append("")

    # Executive Summary
    if include_backup_rds:
        lines.append("EXECUTIVE SUMMARY")
        lines.append("-" * 70)
    else:
        lines.append("EXECUTIVE SUMMARY")

    # Compute totals per check
    totals = {}
    for chk_name, checker in checkers.items():
        total = 0
        for profile in profiles:
            result = all_results.get(profile, {}).get(chk_name, {})
            total += checker.count_issues(result)
        if total > 0:
            totals[chk_name] = total

    summary_text = f"Security assessment completed across {len(profiles)} AWS accounts."
    if check_errors:
        summary_text += f" {len(check_errors)} check error(s) encountered; see CHECK ERRORS section."

    if not totals and not check_errors:
        summary_text += (
            " No new security incidents detected. All systems operating normally."
        )
    elif totals:
        issue_parts = []
        if check_errors:
            issue_parts.append(f"{len(check_errors)} check errors")
        for chk_name, total in totals.items():
            checker = checkers[chk_name]
            if checker.issue_label:
                issue_parts.append(f"{total} {checker.issue_label}")
        if issue_parts:
            summary_text += (
                f" {' and '.join(issue_parts)} detected requiring attention."
            )

    lines.append(summary_text)
    lines.append("")

    # Assessment Results
    if include_backup_rds:
        lines.append("-" * 70)
        lines.append("ASSESSMENT RESULTS")
        lines.append("-" * 70)
    else:
        lines.append("ASSESSMENT RESULTS")
        lines.append("")

    for chk_name, checker in checkers.items():
        if not checker.supports_consolidated:
            continue
        per_check_results = {}
        for profile in profiles:
            per_check_results[profile] = all_results.get(profile, {}).get(chk_name, {})
        section_lines = checker.render_section(
            per_check_results, errors_by_check.get(chk_name, [])
        )
        lines.extend(section_lines)

    # Account Coverage
    lines.append("")
    if include_backup_rds:
        lines.append("-" * 70)
    lines.append("ACCOUNT COVERAGE")
    if include_backup_rds:
        lines.append("-" * 70)
    lines.append(f"Total Assessed: {len(profiles)} accounts")
    if include_backup_rds:
        lines.append(f"Clean Accounts: {len(clean_accounts)}")
        lines.append(f"Accounts with Issues: {len(profiles) - len(clean_accounts)}")
    if check_errors:
        if include_backup_rds:
            lines.append(f"Check Errors: {len(check_errors)} (see below)")
        lines.append("")
        lines.append("CHECK ERRORS:")
        for profile, chk, err in check_errors:
            prefix = "  - " if include_backup_rds else "- "
            lines.append(f"{prefix}{profile} | {chk}: {err}")

    # Recommendations (detailed mode)
    if include_backup_rds:
        lines.append("")
        lines.append("-" * 70)
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 70)
        rec_count = 1

        if check_errors:
            lines.append(
                f"{rec_count}. INVESTIGATE CHECK ERRORS: Resolve authentication/permission/session issues"
            )
            lines.append("   Affected:")
            for profile, chk, err in check_errors[:5]:
                lines.append(f"   - {profile} ({chk}): {err}")
            if len(check_errors) > 5:
                lines.append(f"   ... and {len(check_errors) - 5} more")
            rec_count += 1

        for chk_name, total in totals.items():
            checker = checkers[chk_name]
            if checker.recommendation_text:
                lines.append(f"{rec_count}. {checker.recommendation_text}")
                affected = [
                    p
                    for p in profiles
                    if checker.count_issues(all_results.get(p, {}).get(chk_name, {}))
                    > 0
                ]
                if affected:
                    lines.append(f"   Affected accounts: {', '.join(affected)}")
                rec_count += 1

        if rec_count == 1:
            lines.append("1. ROUTINE MONITORING: Continue assessment schedule")

    # WhatsApp messages for Aryanoble (arbel mode)
    if include_backup_rds and group_name and group_name.lower() == "aryanoble":
        date_str_wa = datetime.now(timezone(timedelta(hours=7))).strftime("%d-%m-%Y")

        lines.append("")
        lines.append("=" * 70)
        lines.append("WHATSAPP MESSAGE (READY TO SEND)")
        lines.append("=" * 70)
        lines.append("--backup")
        wa_results = {
            p: {chk: all_results.get(p, {}).get(chk, {}) for chk in checks}
            for p in profiles
        }
        lines.append(build_whatsapp_backup(date_str_wa, wa_results))
        lines.append("")
        lines.append("--rds")
        lines.append(build_whatsapp_rds(wa_results))

    return "\n".join(lines)


class CheckExecutor:
    """Synchronous check executor for web API.

    Executes checks directly (no queue), saves results to DB,
    and optionally sends to Slack.
    """

    def __init__(
        self,
        check_repo,
        customer_repo,
        region: str,
        max_workers: int = DEFAULT_WORKERS,
        timeout: int = 300,
    ):
        self.check_repo = check_repo
        self.customer_repo = customer_repo
        self.region = region
        self.max_workers = max_workers
        self.timeout = timeout

    def execute(
        self,
        customer_ids: list[str],
        mode: str,
        check_name: str | None = None,
        account_ids: list[str] | None = None,
        send_slack: bool = False,
        region: str | None = None,
        check_params: dict | None = None,
        run_source: str = "api",
        persist_mode: str = "auto",
    ) -> dict:
        """Execute checks for one or more customers and return combined results.

        Args:
            customer_ids: List of database customer IDs (min 1)
            mode: "single", "all", or "arbel"
            check_name: Required for "single" mode
            account_ids: Specific account IDs, or None for all
            send_slack: Whether to send results to Slack
            region: AWS region override; falls back to executor's default region
            check_params: Extra params passed to checker constructor
            run_source: Execution source tag (e.g. "api" or "tui")
            persist_mode: Persistence policy ("auto", "normalized", "none")

        Returns:
            Dict with check_runs list, execution_time, results (flat),
            consolidated_outputs (dict keyed by customer_id)
        """
        start_time = time.time()
        persist_mode_normalized = self._resolve_persist_mode(run_source, persist_mode)
        persist_enabled = persist_mode_normalized == "normalized"
        effective_region = region if region else self.region

        check_runs_list = []
        all_result_items = []
        consolidated_outputs = {}
        backup_overviews = {}
        warnings = []
        processed_customers = 0

        for customer_id in customer_ids:
            # Resolve customer
            customer = self.customer_repo.get_customer(customer_id)
            if customer is None:
                logger.warning(f"Customer not found, skipping: {customer_id}")
                warnings.append(f"Customer not found: {customer_id}")
                continue

            # Resolve accounts
            if account_ids:
                accounts = [
                    acc
                    for acc in customer.accounts
                    if acc.id in account_ids and acc.is_active
                ]
            else:
                accounts = [acc for acc in customer.accounts if acc.is_active]

            if not accounts:
                logger.warning(
                    f"No active accounts for customer {customer_id}, skipping"
                )
                warnings.append(f"No active accounts: {customer_id}")
                continue

            processed_customers += 1

            # Resolve checks to run
            checks_to_run = self._resolve_checks(mode, check_name, customer)

            # Create check run record
            check_run = None
            if persist_enabled:
                check_run = self.check_repo.create_check_run(
                    customer_id=customer_id,
                    check_mode=mode,
                    check_name=check_name if mode == "single" else None,
                )

            # Execute checks in parallel
            raw_results = self._execute_parallel(
                accounts, checks_to_run, effective_region, check_params
            )

            # Build per-profile results structure for consolidated report
            profile_results = {}
            checkers_map = {}
            check_errors = []
            errors_by_check = {}

            for account, check_results in raw_results.items():
                profile = account.profile_name
                profile_results[profile] = {}
                for chk_name, raw_result in check_results.items():
                    profile_results[profile][chk_name] = raw_result
                    checker_inst = raw_result.pop("_checker_instance", None)
                    if checker_inst and chk_name not in checkers_map:
                        checkers_map[chk_name] = checker_inst
                    if raw_result.get("status") == "error":
                        err_msg = raw_result.get("error", "Unknown error")
                        check_errors.append((profile, chk_name, err_msg))
                        errors_by_check.setdefault(chk_name, []).append(
                            (profile, err_msg)
                        )

            # Ensure all checks have a checker instance (even if all errored)
            for chk_name in checks_to_run:
                if chk_name not in checkers_map:
                    checker_class = AVAILABLE_CHECKS.get(chk_name)
                    if checker_class:
                        checkers_map[chk_name] = checker_class(region=effective_region)

            # Determine clean accounts
            profiles = [acc.profile_name for acc in accounts]
            clean_accounts = []
            for profile in profiles:
                has_issues = False
                for chk_name, checker in checkers_map.items():
                    result = profile_results.get(profile, {}).get(chk_name, {})
                    if (
                        result.get("status") == "error"
                        or checker.count_issues(result) > 0
                    ):
                        has_issues = True
                        break
                if not has_issues:
                    clean_accounts.append(profile)

            # Save results to DB and build response items
            result_items = []
            for account, check_results in raw_results.items():
                for chk_name, raw_result in check_results.items():
                    status = _normalize_status(raw_result, chk_name)
                    summary = _build_summary(raw_result, chk_name)
                    output = raw_result.get("_formatted_output", "")

                    details = _json_safe(
                        {k: v for k, v in raw_result.items() if not k.startswith("_")}
                    )

                    if persist_enabled and check_run is not None:
                        self.check_repo.add_result(
                            check_run_id=check_run.id,
                            account_id=account.id,
                            check_name=chk_name,
                            status=status,
                            summary=summary,
                            output=output,
                            details=details,
                        )

                        finding_events = map_check_findings(
                            check_name=chk_name,
                            account_id=account.id,
                            raw_result=raw_result,
                        )
                        if finding_events:
                            self.check_repo.add_finding_events(
                                check_run_id=check_run.id,
                                account_id=account.id,
                                events=finding_events,
                            )

                        metric_samples = map_check_metric_samples(
                            check_name=chk_name,
                            account_id=account.id,
                            raw_result=raw_result,
                        )
                        if metric_samples:
                            self.check_repo.add_metric_samples(
                                check_run_id=check_run.id,
                                account_id=account.id,
                                samples=metric_samples,
                            )

                    result_items.append(
                        {
                            "customer_id": customer_id,
                            "account": {
                                "id": account.id,
                                "profile_name": account.profile_name,
                                "display_name": account.display_name,
                            },
                            "check_name": chk_name,
                            "status": status,
                            "summary": summary,
                            "output": output,
                        }
                    )

            all_result_items.extend(result_items)

            # Build consolidated output for all/arbel modes, or concatenated output for single
            consolidated = ""
            if mode in ("all", "arbel"):
                consolidated = _build_consolidated_report(
                    profiles=profiles,
                    all_results=profile_results,
                    checks=list(checks_to_run.keys()),
                    checkers=checkers_map,
                    check_errors=check_errors,
                    clean_accounts=clean_accounts,
                    errors_by_check=errors_by_check,
                    region=effective_region,
                    group_name=customer.display_name,
                )
                if "backup" in checks_to_run:
                    wa_results = {
                        p: {
                            chk: profile_results.get(p, {}).get(chk, {})
                            for chk in checks_to_run
                        }
                        for p in profiles
                    }
                    backup_overviews[customer_id] = summarize_backup_whatsapp(
                        wa_results
                    )
            elif mode == "single":
                if check_name == "backup":
                    date_str_wa = datetime.now(timezone(timedelta(hours=7))).strftime(
                        "%d-%m-%Y"
                    )
                    wa_results = {
                        p: {
                            chk: profile_results.get(p, {}).get(chk, {})
                            for chk in checks_to_run
                        }
                        for p in profiles
                    }
                    consolidated = build_whatsapp_backup(date_str_wa, wa_results)
                    backup_overviews[customer_id] = summarize_backup_whatsapp(
                        wa_results
                    )
                else:
                    parts = []
                    for item in result_items:
                        acct = item["account"]
                        header = (
                            f"=== {acct['display_name']} ({acct['profile_name']}) ==="
                        )
                        parts.append(header)
                        parts.append(item.get("output", "") or item["summary"])
                        parts.append("")
                    consolidated = "\n".join(parts)

            consolidated_outputs[customer_id] = consolidated

            # Send to Slack if requested
            slack_sent = False
            if send_slack and customer.slack_enabled and customer.slack_webhook_url:
                slack_sent = self._send_slack(customer, consolidated, mode, check_name)

            # Finalize check run
            if persist_enabled and check_run is not None:
                self.check_repo.finish_check_run(
                    check_run_id=check_run.id,
                    execution_time_seconds=round(time.time() - start_time, 2),
                    slack_sent=slack_sent,
                )

                check_runs_list.append(
                    {
                        "customer_id": customer_id,
                        "check_run_id": check_run.id,
                        "slack_sent": slack_sent,
                    }
                )

        if processed_customers == 0:
            raise ValueError(
                f"No valid customers processed. Warnings: {'; '.join(warnings)}"
            )

        if persist_enabled:
            self.check_repo.commit()

        return {
            "check_runs": check_runs_list,
            "execution_time_seconds": round(time.time() - start_time, 2),
            "results": all_result_items,
            "consolidated_outputs": consolidated_outputs,
            "backup_overviews": backup_overviews,
        }

    @staticmethod
    def _resolve_persist_mode(run_source: str, persist_mode: str) -> str:
        mode = (persist_mode or "auto").lower()
        source = (run_source or "api").lower()

        if mode not in {"auto", "normalized", "none"}:
            raise ValueError(f"Invalid persist_mode: {persist_mode}")

        if mode == "auto":
            return "none" if source == "tui" else "normalized"

        return mode

    def _resolve_checks(self, mode: str, check_name: str | None, customer=None) -> dict:
        """Resolve which checks to run based on mode.

        - single: Just the one named check
        - all: Customer's configured checks list (from DB), fallback to ALL_MODE_CHECKS
               Default ALL_MODE_CHECKS: cost, guardduty, cloudwatch, notifications
        - arbel: Fixed ARBEL_CHECKS preset
        """
        if mode == "single":
            if not check_name:
                raise ValueError("check_name required for single mode")
            if check_name not in AVAILABLE_CHECKS:
                raise ValueError(f"Unknown check: {check_name}")
            return {check_name: AVAILABLE_CHECKS[check_name]}

        elif mode == "all":
            # Read from customer.checks (database) if available
            if customer and hasattr(customer, "checks") and customer.checks:
                resolved = {}
                for chk in customer.checks:
                    if chk in AVAILABLE_CHECKS:
                        resolved[chk] = AVAILABLE_CHECKS[chk]
                    else:
                        logger.warning(
                            f"Unknown check '{chk}' in customer config, skipping"
                        )
                if resolved:
                    return resolved
            # Fallback to default all-mode checks
            return dict(ALL_MODE_CHECKS)

        elif mode == "arbel":
            resolved = {}
            for chk in ARBEL_CHECKS:
                if chk in AVAILABLE_CHECKS:
                    resolved[chk] = AVAILABLE_CHECKS[chk]
            return resolved

        else:
            raise ValueError(f"Invalid mode: {mode}")

    def _execute_parallel(
        self,
        accounts: list,
        checks: dict,
        region: str,
        check_params: dict | None = None,
    ) -> dict:
        """Run checks across accounts in parallel."""
        results = {}

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}

            # Pre-extract per-account alarm overrides and remaining params from check_params
            per_account_alarms: dict = {}
            remaining_check_params: dict | None = None
            if check_params:
                per_account_alarms = check_params.get("account_alarm_names") or {}
                remaining_check_params = {
                    k: v for k, v in check_params.items() if k != "account_alarm_names"
                } or None  # empty dict → None to skip the merge block

            for account in accounts:
                for chk_name, _checker_class in checks.items():
                    # Start with config_extra from DB
                    check_kwargs = None
                    if account.config_extra and chk_name in account.config_extra:
                        check_kwargs = dict(account.config_extra[chk_name])

                    # Merge per-account check configs from DB table
                    account_check_configs = (
                        getattr(account, "check_configs", None) or []
                    )
                    for row in account_check_configs:
                        if getattr(row, "check_name", None) == chk_name and isinstance(
                            getattr(row, "config", None), dict
                        ):
                            if check_kwargs is None:
                                check_kwargs = {}
                            check_kwargs.update(row.config)
                            break

                    # Inject alarm_names from DB for cloudwatch and alarm_verification checks
                    if (
                        chk_name in ("cloudwatch", "alarm_verification")
                        and account.alarm_names
                    ):
                        if check_kwargs is None:
                            check_kwargs = {}
                        check_kwargs.setdefault("alarm_names", account.alarm_names)

                    # Apply per-account alarm_names override unconditionally; checks that
                    # don't accept alarm_names will ignore it via **kwargs or their own constructor
                    account_alarms = per_account_alarms.get(str(account.id))
                    if account_alarms:
                        if check_kwargs is None:
                            check_kwargs = {}
                        check_kwargs["alarm_names"] = account_alarms

                    # Merge remaining check_params (e.g. window_hours) — overrides everything
                    if remaining_check_params:
                        if check_kwargs is None:
                            check_kwargs = {}
                        check_kwargs.update(remaining_check_params)

                    # Use account's own region if set, otherwise fall back to effective_region
                    region_for_account = account.region or region

                    future = executor.submit(
                        _run_single_check,
                        chk_name,
                        account.profile_name,
                        region_for_account,
                        check_kwargs,
                    )
                    futures[future] = (account, chk_name)

            done, pending = wait(
                futures.keys(),
                timeout=self.timeout,
                return_when=ALL_COMPLETED,
            )

            for future in done:
                account, chk_name = futures[future]
                try:
                    raw_result = future.result()
                except Exception as exc:
                    raw_result = {"status": "error", "error": str(exc)}

                if account not in results:
                    results[account] = {}
                results[account][chk_name] = raw_result

            for future in pending:
                account, chk_name = futures[future]
                future.cancel()
                if account not in results:
                    results[account] = {}
                results[account][chk_name] = {
                    "status": "error",
                    "error": f"Check timed out after {self.timeout}s",
                }

        return results

    def _send_slack(
        self,
        customer,
        report_text: str,
        mode: str,
        check_name: str | None,
    ) -> bool:
        """Send consolidated report text to customer's Slack webhook."""
        if not report_text:
            return False

        header = f"Monitoring Report: {customer.display_name}"
        if mode == "single" and check_name:
            header += f" ({check_name})"
        else:
            header += f" ({mode} mode)"

        text = f"{header}\n\n{report_text}"

        sent, reason = send_to_webhook(
            customer.slack_webhook_url, text, channel=customer.slack_channel
        )
        if not sent:
            logger.warning(
                f"Slack delivery failed for {customer.display_name}: {reason}"
            )
        return sent
