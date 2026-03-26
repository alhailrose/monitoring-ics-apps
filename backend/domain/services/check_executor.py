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
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, date, timedelta, timezone
from typing import Optional

from backend.domain.runtime.config import (
    AVAILABLE_CHECKS,
    ALL_MODE_CHECKS,
    DEFAULT_WORKERS,
)
from backend.domain.runtime.utils import get_account_id as get_account_id_from_profile
from backend.domain.runtime.reports import (
    build_whatsapp_backup_aryanoble,
    build_whatsapp_rds,
    summarize_backup_whatsapp,
)
from backend.domain.finding_events import FINDING_EVENT_CHECKS
from backend.domain.services.finding_events_mapper import map_check_findings
from backend.domain.services.metric_samples_mapper import map_check_metric_samples
from backend.checks.common.aws_errors import (
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
    from decimal import Decimal

    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
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
    if check_name == "backup":
        failed = int(raw_result.get("failed_jobs", 0) or 0)
        expired = int(raw_result.get("expired_jobs", 0) or 0)
        total = int(raw_result.get("total_jobs", 0) or 0)
        vaults = raw_result.get("vaults") or []
        vault_ok = sum(
            1
            for v in vaults
            if not v.get("error") and v.get("recovery_points_24h", 0) > 0
        )
        vault_fail = sum(
            1 for v in vaults if v.get("error") or v.get("recovery_points_24h", 0) == 0
        )
        if vaults and total == 0:
            # Vault-only account
            if vault_fail > 0:
                return f"{vault_fail} vault(s) no backup today"
            return f"{vault_ok} vault(s) OK"
        parts = [f"{total} jobs"]
        if failed > 0:
            parts.append(f"{failed} failed")
        if expired > 0:
            parts.append(f"{expired} expired")
        if not failed and not expired:
            parts.append("all OK")
        return ", ".join(parts)
    if check_name == "ec2_utilization":
        summary_dict = raw_result.get("summary", {})
        if isinstance(summary_dict, dict):
            warn = summary_dict.get("warning", 0)
            crit = summary_dict.get("critical", 0)
            total = summary_dict.get("total", 0)
            if crit > 0 or warn > 0:
                return f"{warn} warning, {crit} critical (of {total})"
            return f"All normal ({total} total)"
    return str(raw_result.get("summary", "Check completed"))


def _build_creds_for_account(account, region: str | None = None) -> dict:
    """Resolve credentials for an account based on its auth_method.

    Returns a dict with keys:
      aws_access_key_id, aws_secret_access_key, aws_session_token (may be None)

    Callers should create their own boto3.Session from these credentials rather
    than sharing a single Session across threads, to avoid any profile/env state
    leaking in.
    """
    import boto3
    from backend.utils.crypto import decrypt_secret
    from backend.config.settings import get_settings

    auth_method = getattr(account, "auth_method", "profile") or "profile"
    effective_region = region or getattr(account, "region", None)

    if auth_method == "access_key":
        key_id = account.aws_access_key_id
        secret_enc = account.aws_secret_access_key_enc
        logger.info(
            "[auth] access_key creds for '%s': key_id=%s, secret_enc_set=%s",
            account.profile_name,
            key_id,
            bool(secret_enc),
        )
        if not key_id or not secret_enc:
            raise ValueError(
                f"Account '{account.profile_name}' missing access key credentials"
            )
        secret = decrypt_secret(secret_enc, get_settings().jwt_secret)
        return {
            "aws_access_key_id": key_id,
            "aws_secret_access_key": secret,
            "aws_session_token": None,
        }

    elif auth_method == "assumed_role":
        role_arn = account.role_arn
        if not role_arn:
            raise ValueError(
                f"Account '{account.profile_name}' missing role_arn for assumed_role"
            )
        # Build base session for STS call: access_key if available, else profile
        if account.aws_access_key_id and account.aws_secret_access_key_enc:
            secret = decrypt_secret(
                account.aws_secret_access_key_enc, get_settings().jwt_secret
            )
            base_session = boto3.Session(
                aws_access_key_id=account.aws_access_key_id,
                aws_secret_access_key=secret,
                aws_session_token=None,
                region_name=effective_region,
            )
        else:
            base_session = boto3.Session(
                profile_name=account.profile_name, region_name=effective_region
            )
        sts = base_session.client("sts", region_name="us-east-1")
        assume_kwargs: dict = {
            "RoleArn": role_arn,
            "RoleSessionName": f"monitoring-hub-{account.profile_name}",
        }
        if account.external_id:
            assume_kwargs["ExternalId"] = account.external_id
        creds = sts.assume_role(**assume_kwargs)["Credentials"]
        return {
            "aws_access_key_id": creds["AccessKeyId"],
            "aws_secret_access_key": creds["SecretAccessKey"],
            "aws_session_token": creds["SessionToken"],
        }

    else:  # profile — no injected credentials; checker uses its own profile session
        return None


def _run_single_check(
    check_name: str,
    profile: str,
    region: str,
    check_kwargs: Optional[dict] = None,
    injected_creds: dict | None = None,
    account_id: str | None = None,
) -> dict:
    """Run one check on one profile, return raw result."""
    checker_class = AVAILABLE_CHECKS.get(check_name)
    if checker_class is None:
        return {"status": "error", "error": f"Unknown check: {check_name}"}

    if not account_id or account_id == "Unknown":
        account_id = get_account_id_from_profile(profile)
    checker = checker_class(region=region, **(check_kwargs or {}))
    if injected_creds is not None:
        checker._injected_creds = injected_creds
        logger.info(
            "[auth] Injected creds into %s for profile '%s' (key=%s)",
            checker_class.__name__,
            profile,
            injected_creds.get("aws_access_key_id"),
        )

    try:
        result = checker.check(profile, account_id)
        if result.get("status") == "error":
            logger.warning(
                "[check] %s/%s returned error: %s",
                check_name,
                profile,
                result.get("error"),
            )
        try:
            result["_formatted_output"] = checker.format_report(result)
        except Exception:
            result["_formatted_output"] = str(result)
        # Attach checker instance for consolidated report building
        result["_checker_instance"] = checker
        return result
    except Exception as exc:
        if is_credential_error(exc):
            logger.warning(
                "[auth] Credential error in %s for profile '%s': %s",
                check_name,
                profile,
                exc,
            )
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
        lines.append(
            build_whatsapp_backup_aryanoble(
                date_str_wa, wa_results, group_name=group_name
            )
        )
        lines.append("")
        lines.append("--rds")
        lines.append(build_whatsapp_rds(wa_results))

    return "\n".join(lines)


def _build_summary_report(
    profiles: list[str],
    all_results: dict[str, dict[str, dict]],
    checks: list[str],
    checkers: dict,
    check_errors: list[tuple],
    clean_accounts: list[str],
    region: str,
    group_name: str | None = None,
    accounts: list | None = None,
) -> str:
    """Build a condensed summary report (WhatsApp-friendly).

    Used when customer.report_mode == "summary". Produces a compact daily
    alert format with utilization metrics and brief other-check summaries.

    Output format matches the WhatsApp monitoring message template:
      Selamat Pagi Team
      Berikut Alert Monitoring
      YYYY.MM.DD

      Utilisasi X Jam (CPU/MEM/DISK)
      - AccountName (account_id)
          - InstanceName | CPU(avg)=X% | MEM(avg)=Y% | DISK=Z%
        *Catatan Alert:*
          ...

      Ringkasan Check Lain
      - Notifikasi: ...
      - Cost Anomaly: ...
      - GuardDuty: ...
      - Alarm CloudWatch: ...
    """
    now_jkt = datetime.now(timezone(timedelta(hours=7)))
    if 5 <= now_jkt.hour < 11:
        greeting = "Selamat Pagi"
    elif 11 <= now_jkt.hour < 15:
        greeting = "Selamat Siang"
    elif 15 <= now_jkt.hour < 18:
        greeting = "Selamat Sore"
    else:
        greeting = "Selamat Malam"

    date_str = now_jkt.strftime("%Y.%m.%d")

    # Build profile → display_name map from DB accounts
    profile_display: dict[str, str] = {}
    profile_aws_id: dict[str, str] = {}
    for acc in accounts or []:
        profile_display[acc.profile_name] = acc.display_name
        if acc.account_id:
            profile_aws_id[acc.profile_name] = acc.account_id

    lines = []
    lines.append(f"{greeting} Team")
    lines.append("Berikut Alert Monitoring")
    lines.append(date_str)

    # ── Utilization section ──────────────────────────────────────────────
    utilization_checks = [
        c
        for c in checks
        if c
        in (
            "daily-arbel",
            "daily-arbel-rds",
            "daily-arbel-ec2",
            "aws-utilization-3core",
            "ec2_utilization",
        )
    ]
    if utilization_checks:
        # Detect window_hours from first available result
        window_hours = 12
        for profile in profiles:
            for chk in utilization_checks:
                res = all_results.get(profile, {}).get(chk, {})
                wh = res.get("window_hours") or (res.get("util_window") or {}).get(
                    "hours"
                )
                if wh:
                    window_hours = int(wh)
                    break
            else:
                continue
            break

        lines.append("")
        lines.append(f"Utilisasi {window_hours} Jam (CPU/MEM/DISK)")

        for profile in profiles:
            account_lines = []
            alert_notes = []
            account_label = None
            account_id_str = None

            for chk in utilization_checks:
                res = all_results.get(profile, {}).get(chk, {})
                if not res or res.get("status") in ("error", "skipped"):
                    continue

                if not account_label:
                    account_label = res.get("account_name") or profile_display.get(
                        profile, profile
                    )
                    account_id_str = res.get("account_id") or profile_aws_id.get(
                        profile, ""
                    )

                # ── aws-utilization-3core / ec2_utilization format ──
                if (
                    chk in ("aws-utilization-3core", "ec2_utilization")
                    and res.get("status") == "success"
                ):
                    for row in res.get("instances", []):
                        inst_name = row.get("name") or row.get("instance_id") or "-"
                        parts = []

                        cpu_avg = row.get("cpu_avg_12h")
                        cpu_peak = row.get("cpu_peak_12h")
                        cpu_peak_at = row.get("cpu_peak_at_12h")
                        mem_avg = row.get("memory_avg_12h")
                        mem_peak = row.get("memory_peak_12h")
                        disk_free = row.get("disk_free_min_percent")

                        if cpu_avg is not None:
                            parts.append(f"CPU(avg)={cpu_avg:.2f}%")
                        if mem_avg is not None:
                            parts.append(f"MEM(avg)={mem_avg:.2f}%")
                        if disk_free is not None:
                            parts.append(f"DISK={disk_free:.2f}%")

                        if parts:
                            account_lines.append(
                                f"    - {inst_name} | {' | '.join(parts)}"
                            )

                        # Alert notes for spikes
                        inst_status = str(row.get("status") or "").upper()
                        if inst_status in ("WARNING", "CRITICAL"):
                            if (
                                cpu_peak is not None
                                and cpu_avg is not None
                                and cpu_peak > cpu_avg * 1.5
                            ):
                                time_str = f" pada {cpu_peak_at}" if cpu_peak_at else ""
                                alert_notes.append(
                                    f"*CPU {inst_name} sempat sangat tinggi {cpu_peak:.2f}%{time_str} (avg={cpu_avg:.2f}%).*"
                                )
                            if (
                                mem_avg is not None
                                and mem_peak is not None
                                and mem_peak > 80
                            ):
                                alert_notes.append(
                                    f"*Memory {inst_name} tinggi dan konsisten dalam {window_hours} jam terakhir (avg={mem_avg:.2f}%, peak={mem_peak:.2f}%).*"
                                )
                            if disk_free is not None and disk_free < 10:
                                alert_notes.append(
                                    f"*Disk {inst_name} sangat rendah (sisa minimum {disk_free:.2f}%).*"
                                )
                    continue

                # ── daily-arbel / daily-arbel-rds / daily-arbel-ec2 format ──
                # Process main instances + extra_sections
                all_sections = [res]
                for section in res.get("extra_sections") or []:
                    if isinstance(section, dict):
                        all_sections.append(section)

                for section in all_sections:
                    instances = section.get("instances", {})
                    for role, data in instances.items():
                        inst_name = (
                            data.get("instance_name") or data.get("instance_id") or role
                        )
                        metrics = data.get("metrics", {})

                        # Collect metric values
                        parts = []

                        for metric_name, info in metrics.items():
                            avg = info.get("avg")
                            last = info.get("last")
                            max_val = info.get("max")
                            status = info.get("status", "ok")

                            if metric_name == "CPUUtilization":
                                val = avg if avg is not None else last
                                if val is not None:
                                    parts.append(f"CPU(avg)={val:.2f}%")
                                    if (
                                        status in ("warn", "past-warn")
                                        and max_val is not None
                                        and max_val > val * 1.5
                                    ):
                                        peak_time_str = ""
                                        timestamps = info.get("timestamps", [])
                                        values = info.get("values", [])
                                        if (
                                            timestamps
                                            and values
                                            and len(timestamps) == len(values)
                                        ):
                                            max_idx = values.index(max(values))
                                            peak_ts = timestamps[max_idx]
                                            if hasattr(peak_ts, "strftime"):
                                                jkt_tz = timezone(timedelta(hours=7))
                                                peak_jkt = (
                                                    peak_ts.astimezone(jkt_tz)
                                                    if peak_ts.tzinfo
                                                    else peak_ts
                                                )
                                                peak_time_str = f" pada {peak_jkt.strftime('%Y-%m-%d %H:%M:%S')} +07"
                                        alert_notes.append(
                                            f"*CPU {inst_name} sempat sangat tinggi {max_val:.2f}%{peak_time_str} (avg={val:.2f}%).*"
                                        )

                            elif metric_name == "ACUUtilization":
                                val = avg if avg is not None else last
                                if val is not None:
                                    parts.append(f"ACU(avg)={val:.2f}%")

                            elif metric_name == "FreeableMemory":
                                val = avg if avg is not None else last
                                if val is not None:
                                    gb = val / (1024**3)
                                    parts.append(f"MEM(avg)={gb:.2f}GB")
                                    if status == "warn":
                                        values = info.get("values", [val])
                                        peak_gb = (
                                            min(values) / (1024**3) if values else gb
                                        )
                                        alert_notes.append(
                                            f"*Memory {inst_name} rendah dan konsisten dalam {window_hours} jam terakhir (avg={gb:.2f}GB, min={peak_gb:.2f}GB).*"
                                        )

                            elif metric_name == "FreeStorageSpace":
                                val = (
                                    last
                                    if last is not None
                                    else (avg if avg is not None else None)
                                )
                                if val is not None:
                                    gb = val / (1024**3)
                                    parts.append(f"DISK={gb:.2f}GB")
                                    if status == "warn":
                                        alert_notes.append(
                                            f"*Disk {inst_name} sangat rendah (sisa {gb:.2f}GB).*"
                                        )

                            elif metric_name == "DatabaseConnections":
                                val = (
                                    last
                                    if last is not None
                                    else (avg if avg is not None else None)
                                )
                                if val is not None:
                                    parts.append(f"CONN={int(val)}")

                        # EC2 disk_memory_alarms for alert notes
                        for alarm in data.get("disk_memory_alarms") or []:
                            alarm_name = alarm.get("alarm_name", "")
                            state = alarm.get("current_state", "")
                            periods = alarm.get("periods") or []
                            if "mem" in alarm_name.lower():
                                if state == "ALARM":
                                    alert_notes.append(
                                        f"*Memory {inst_name} dalam kondisi ALARM.*"
                                    )
                                elif periods:
                                    alert_notes.append(
                                        f"*Memory {inst_name} sempat ALARM dalam {window_hours} jam terakhir.*"
                                    )
                            elif "disk" in alarm_name.lower():
                                if state == "ALARM":
                                    alert_notes.append(
                                        f"*Disk {inst_name} dalam kondisi ALARM.*"
                                    )
                                elif periods:
                                    alert_notes.append(
                                        f"*Disk {inst_name} sempat ALARM dalam {window_hours} jam terakhir.*"
                                    )

                        if parts:
                            account_lines.append(
                                f"    - {inst_name} | {' | '.join(parts)}"
                            )

            if account_label and (account_lines or alert_notes):
                lines.append(f"- {account_label} ({account_id_str})")
                lines.extend(account_lines)
                if alert_notes:
                    lines.append("  *Catatan Alert:*")
                    for note in alert_notes:
                        lines.append(f"    - {note}")

    def _trim_text(value: str, max_len: int = 72) -> str:
        text = " ".join(str(value or "").split())
        if len(text) <= max_len:
            return text
        return text[: max_len - 3].rstrip() + "..."

    def _example_items(values: list[str], max_items: int = 2) -> list[str]:
        seen = []
        for val in values:
            cleaned = _trim_text(val)
            if cleaned and cleaned not in seen:
                seen.append(cleaned)
        if not seen:
            return []
        shown = seen[:max_items]
        lines = [f"  • {name}" for name in shown]
        extra_count = len(seen) - max_items
        if extra_count > 0:
            lines.append(f"  • +{extra_count} lainnya")
        return lines

    # ── Other checks summary ────────────────────────────────────────────
    other_checks = [c for c in checks if c not in utilization_checks]
    if other_checks or check_errors:
        lines.append("")
        lines.append("Ringkasan Check Lain")

        # Notifications
        if "notifications" in checks:
            total_notif = 0
            notif_examples = []
            for profile in profiles:
                res = all_results.get(profile, {}).get("notifications", {})
                total_notif += int(res.get("recent_count", 0))
                for event in res.get("recent_events") or []:
                    notif_event = (
                        event.get("notificationEvent", {})
                        if isinstance(event, dict)
                        else {}
                    )
                    headline = (
                        notif_event.get("messageComponents", {}).get("headline")
                        if isinstance(notif_event, dict)
                        else None
                    )
                    event_type = (
                        notif_event.get("sourceEventMetadata", {}).get("eventType")
                        if isinstance(notif_event, dict)
                        else None
                    )
                    candidate = headline or event_type
                    if candidate:
                        notif_examples.append(str(candidate))
            window = 12
            for profile in profiles:
                res = all_results.get(profile, {}).get("notifications", {})
                if res.get("window_hours"):
                    window = int(res["window_hours"])
                    break
            if total_notif == 0:
                lines.append(f"- Notifikasi ({window} jam): tidak ada notifikasi baru")
            else:
                lines.append(
                    f"- Notifikasi ({window} jam): {total_notif} notifikasi baru"
                )
                lines.extend(_example_items(notif_examples))

        # Cost Anomaly
        if "cost" in checks:
            total_anomalies = 0
            for profile in profiles:
                res = all_results.get(profile, {}).get("cost", {})
                total_anomalies += int(res.get("total_anomalies", 0))
            if total_anomalies == 0:
                lines.append("- Cost Anomaly: tidak ada cost anomaly")
            else:
                lines.append(
                    f"- Cost Anomaly: {total_anomalies} cost anomaly terdeteksi"
                )

        # GuardDuty
        if "guardduty" in checks:
            disabled_accounts = []
            finding_accounts = []
            total_findings = 0
            finding_examples = []
            for profile in profiles:
                res = all_results.get(profile, {}).get("guardduty", {})
                acct_name = profile_display.get(
                    profile, res.get("account_name", profile)
                )
                acct_id = res.get("account_id") or profile_aws_id.get(profile, "")
                label = f"{acct_name} ({acct_id})" if acct_id else acct_name
                if res.get("status") == "disabled":
                    disabled_accounts.append(label)
                elif int(res.get("findings", 0)) > 0:
                    count = int(res["findings"])
                    total_findings += count
                    finding_accounts.append((label, count))
                    for detail in res.get("details") or []:
                        if not isinstance(detail, dict):
                            continue
                        candidate = detail.get("title") or detail.get("type")
                        if candidate:
                            finding_examples.append(str(candidate))
            if disabled_accounts and not finding_accounts:
                lines.append(
                    f"- GuardDuty Finding: tidak aktif pada {', '.join(disabled_accounts)}"
                )
            elif finding_accounts:
                parts = [
                    f"{count} finding pada {label}" for label, count in finding_accounts
                ]
                msg = "- GuardDuty Finding: " + ", ".join(parts)
                if disabled_accounts:
                    msg += f" (tidak aktif pada {', '.join(disabled_accounts)})"
                lines.append(msg)
                lines.extend(_example_items(finding_examples))
            else:
                lines.append("- GuardDuty Finding: tidak ada finding baru")

        # CloudWatch Alarms
        if "cloudwatch" in checks:
            total_alarms = 0
            alarm_accounts = []
            alarm_examples = []
            for profile in profiles:
                res = all_results.get(profile, {}).get("cloudwatch", {})
                count = int(res.get("count", 0))
                if count > 0:
                    total_alarms += count
                    acct_name = profile_display.get(
                        profile, res.get("account_name", profile)
                    )
                    acct_id = res.get("account_id") or profile_aws_id.get(profile, "")
                    label = f"{acct_name} ({acct_id})" if acct_id else acct_name
                    alarm_accounts.append((label, count))
                    for detail in res.get("details") or []:
                        if not isinstance(detail, dict):
                            continue
                        name = detail.get("name")
                        if name:
                            alarm_examples.append(str(name))
            if total_alarms == 0:
                lines.append("- Alarm CloudWatch: tidak ada alarm aktif")
            else:
                parts = [
                    f"{count} alarm pada {label}" for label, count in alarm_accounts
                ]
                lines.append(f"- Alarm CloudWatch: {', '.join(parts)}")
                lines.extend(_example_items(alarm_examples))

        # Backup
        if "backup" in checks:
            failed = 0
            for profile in profiles:
                res = all_results.get(profile, {}).get("backup", {})
                failed += int(res.get("failed_jobs", 0))
            if failed == 0:
                lines.append("- Backup: semua backup berhasil")
            else:
                lines.append(f"- Backup: {failed} job backup gagal")

    # Check errors at the end
    if check_errors:
        lines.append("")
        lines.append("*Error:*")
        for profile, chk, err in check_errors[:5]:
            lines.append(f"- {profile} ({chk}): {err}")
        if len(check_errors) > 5:
            lines.append(f"... +{len(check_errors) - 5} lainnya")

    return "\n".join(lines)


def _build_simple_report(
    profiles: list[str],
    all_results: dict[str, dict[str, dict]],
    checks: list[str],
) -> str:
    """Build a minimal flat-list report — one alarm/finding name per line.

    Format:
      Selamat Pagi
      Berikut Alert Pagi ini
      YYYY.MM.DD

      AlarmName1
      AlarmName2
      ...

    If nothing is in alarm, ends with "tidak ada alarm aktif".
    Designed for customers like Frisian Flag that use CloudWatch only and want
    a clean copy-paste message.
    """
    now_jkt = datetime.now(timezone(timedelta(hours=7)))
    if 5 <= now_jkt.hour < 11:
        time_label = "Pagi"
    elif 11 <= now_jkt.hour < 15:
        time_label = "Siang"
    elif 15 <= now_jkt.hour < 18:
        time_label = "Sore"
    else:
        time_label = "Malam"

    date_str = now_jkt.strftime("%Y.%m.%d")

    lines = [
        f"Selamat {time_label}",
        f"Berikut Alert {time_label} ini",
        date_str,
    ]

    alarm_names: list[str] = []

    for chk in checks:
        for profile in profiles:
            res = all_results.get(profile, {}).get(chk, {})
            if not res or res.get("status") == "error":
                continue

            if chk == "cloudwatch":
                for detail in res.get("details", []):
                    name = detail.get("name", "")
                    if name:
                        alarm_names.append(name)

            elif chk == "guardduty":
                count = int(res.get("findings", 0) or 0)
                if count > 0:
                    alarm_names.append(f"GuardDuty: {count} finding(s) detected")

            elif chk == "notifications":
                count = int(res.get("recent_count", 0) or 0)
                if count > 0:
                    alarm_names.append(f"Notifications: {count} baru")

            elif chk == "backup":
                failed = int(res.get("failed_jobs", 0) or 0)
                if failed > 0:
                    alarm_names.append(f"Backup: {failed} job gagal")

            elif chk == "cost":
                count = int(res.get("total_anomalies", 0) or 0)
                if count > 0:
                    alarm_names.append(f"Cost Anomaly: {count} terdeteksi")

    if alarm_names:
        lines.append("")
        lines.extend(alarm_names)
    else:
        lines.append("")
        lines.append("tidak ada alarm aktif")

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
        customer_labels = {}
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
            customer_labels[customer_id] = (
                getattr(customer, "display_name", None)
                or getattr(customer, "name", None)
                or customer_id
            )

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
                        if (
                            chk_name in FINDING_EVENT_CHECKS
                            and raw_result.get("status") != "error"
                        ):
                            for fe in finding_events:
                                if "raw_payload" in fe:
                                    fe["raw_payload"] = _json_safe(fe["raw_payload"])
                            self.check_repo.add_finding_events(
                                check_run_id=check_run.id,
                                account_id=account.id,
                                events=finding_events,
                                check_name=chk_name,
                            )

                        metric_samples = map_check_metric_samples(
                            check_name=chk_name,
                            account_id=account.id,
                            raw_result=raw_result,
                        )
                        if metric_samples:
                            for ms in metric_samples:
                                if "raw_payload" in ms:
                                    ms["raw_payload"] = _json_safe(ms["raw_payload"])
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
                            "details": details,
                        }
                    )

            all_result_items.extend(result_items)

            # Build consolidated output for all/arbel modes, or concatenated output for single
            consolidated = ""
            report_mode = getattr(customer, "report_mode", "detailed") or "detailed"
            if mode == "arbel":
                # Arbel: one consolidated output per account (keyed by account display_name)
                for account in accounts:
                    acct_profile = account.profile_name
                    acct_results = profile_results.get(acct_profile, {})
                    if not acct_results:
                        continue
                    parts = []
                    for chk_name, checker in checkers_map.items():
                        raw = acct_results.get(chk_name)
                        if raw:
                            text = checker.format_report(raw)
                            if text and str(text).strip():
                                parts.append(str(text).strip())
                    if parts:
                        consolidated_outputs[account.display_name] = "\n\n".join(parts)
                consolidated = (
                    None  # already stored above; skip the generic store below
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
            elif mode == "all":
                if report_mode == "simple":
                    consolidated = _build_simple_report(
                        profiles=profiles,
                        all_results=profile_results,
                        checks=list(checks_to_run.keys()),
                    )
                elif report_mode == "summary":
                    consolidated = _build_summary_report(
                        profiles=profiles,
                        all_results=profile_results,
                        checks=list(checks_to_run.keys()),
                        checkers=checkers_map,
                        check_errors=check_errors,
                        clean_accounts=clean_accounts,
                        region=effective_region,
                        group_name=customer.display_name,
                        accounts=accounts,
                    )
                else:
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
                    consolidated = build_whatsapp_backup_aryanoble(
                        date_str_wa, wa_results, group_name=customer.display_name
                    )
                    backup_overviews[customer_id] = summarize_backup_whatsapp(
                        wa_results
                    )
                else:
                    # For Arbel single checks, expose one consolidated output per account.
                    is_arbel_single = check_name in {
                        "daily-arbel",
                        "daily-arbel-rds",
                        "daily-arbel-ec2",
                    }
                    if is_arbel_single:
                        for item in result_items:
                            acct_name = item.get("account", {}).get("display_name", "")
                            output_text = item.get("output", "") or item.get(
                                "summary", ""
                            )
                            if acct_name and output_text:
                                consolidated_outputs[acct_name] = output_text
                        consolidated = None
                    else:
                        # Single-check mode: combine per-account format_report outputs
                        # with account name headers so the user can copy a full report.
                        combined_parts = []
                        for item in result_items:
                            acct_name = item.get("account", {}).get("display_name", "")
                            output_text = item.get("output", "") or item.get(
                                "summary", ""
                            )
                            if output_text:
                                header = f"[{acct_name}]" if acct_name else ""
                                combined_parts.append(
                                    f"{header}\n{output_text}".strip()
                                )
                        consolidated = (
                            "\n\n".join(combined_parts) if combined_parts else None
                        )

            if consolidated is not None:
                consolidated_outputs[customer_id] = consolidated

            # Send to Slack if requested
            slack_sent = False
            slack_text = consolidated or ""
            if not slack_text and mode == "single":
                # For single mode, combine per-account outputs for Slack
                slack_text = "\n\n".join(
                    item.get("output", "") or item["summary"] for item in result_items
                )
            if send_slack and customer.slack_enabled and customer.slack_webhook_url:
                slack_sent = self._send_slack(customer, slack_text, mode, check_name)

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

        return _json_safe(
            {
                "mode": mode,
                "check_runs": check_runs_list,
                "execution_time_seconds": round(time.time() - start_time, 2),
                "results": all_result_items,
                "consolidated_outputs": consolidated_outputs,
                "customer_labels": customer_labels,
                "backup_overviews": backup_overviews,
            }
        )

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
                # Resolve credentials for non-profile auth methods
                auth_method = getattr(account, "auth_method", "profile") or "profile"
                injected_creds = None
                if auth_method != "profile":
                    try:
                        injected_creds = _build_creds_for_account(account, region)
                    except Exception as exc:
                        logger.warning(
                            "Auth setup failed for account %s: %s",
                            account.profile_name,
                            exc,
                        )
                        for chk_name in checks:
                            results.setdefault(account, {})[chk_name] = {
                                "status": "error",
                                "error": f"Auth setup: {exc}",
                            }
                        continue

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

                    # Inject stored EC2 instance list from discovery for ec2_utilization
                    if chk_name == "ec2_utilization":
                        discovery = (account.config_extra or {}).get("_discovery", {})
                        ec2_instances = discovery.get("ec2_instances") or []
                        if ec2_instances:
                            if check_kwargs is None:
                                check_kwargs = {}
                            check_kwargs.setdefault(
                                "instance_list",
                                [
                                    {
                                        "instance_id": inst["instance_id"],
                                        "name": inst.get("name", "-"),
                                        "os_type": (
                                            "windows"
                                            if "windows"
                                            in (inst.get("platform") or "").lower()
                                            else "linux"
                                        ),
                                        "instance_type": inst.get("instance_type", ""),
                                        "region": inst["region"],
                                    }
                                    for inst in ec2_instances
                                    if inst.get("instance_id") and inst.get("region")
                                ],
                            )

                    # Inject account display_name for daily-budget so it doesn't
                    # rely on the hardcoded ACCOUNT_LABELS dict in the checker
                    if chk_name == "daily-budget" and account.display_name:
                        if check_kwargs is None:
                            check_kwargs = {}
                        check_kwargs.setdefault("account_name", account.display_name)

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
                        injected_creds,
                        account.account_id,
                    )
                    futures[future] = (account, chk_name)

            # Per-check timeout: each check gets at most PER_CHECK_TIMEOUT seconds.
            # Total wall-clock is still bounded by self.timeout (batch ceiling).
            per_check_timeout = min(60, self.timeout)
            batch_deadline = time.monotonic() + self.timeout

            for future in as_completed(futures.keys(), timeout=self.timeout):
                account, chk_name = futures[future]
                remaining = batch_deadline - time.monotonic()
                try:
                    raw_result = future.result(
                        timeout=max(0.1, min(per_check_timeout, remaining))
                    )
                except TimeoutError:
                    raw_result = {
                        "status": "error",
                        "error": (
                            f"Check '{chk_name}' on '{account.display_name}' "
                            f"timed out after {per_check_timeout}s"
                        ),
                    }
                except Exception as exc:
                    raw_result = {"status": "error", "error": str(exc)}

                if account not in results:
                    results[account] = {}
                results[account][chk_name] = raw_result

            # Mark any futures not yet collected as timed-out (batch deadline exceeded)
            for future, (account, chk_name) in futures.items():
                if account not in results or chk_name not in results.get(account, {}):
                    future.cancel()
                    results.setdefault(account, {})[chk_name] = {
                        "status": "error",
                        "error": (
                            f"Check '{chk_name}' on '{account.display_name}' "
                            f"cancelled — batch timeout of {self.timeout}s exceeded"
                        ),
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
