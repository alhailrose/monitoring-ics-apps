"""
Report generation and summarization functions for AWS Monitoring Hub
"""

from datetime import datetime, timedelta, timezone

from .config import BACKUP_DISPLAY_NAMES
from .utils import get_account_id


def summarize_health(results):
    total = results.get("total_events", 0)
    action_req = results.get("action_required", 0)
    status = "ATTENTION REQUIRED" if action_req > 0 else "OK"
    detail = f"{total} events; {action_req} need action"
    return status, detail


def summarize_cost(results):
    if results.get("status") == "error":
        return "ERROR", results.get("error", "Unknown error")
    monitors = results.get("total_monitors", 0)
    anomalies = results.get("total_anomalies", 0)
    status = "ANOMALIES DETECTED" if anomalies > 0 else "OK"
    detail = f"{monitors} monitors; {anomalies} anomalies (30d)"
    return status, detail


def summarize_guardduty(results):
    if results.get("status") == "error":
        return "ERROR", results.get("error", "Unknown error")
    if results["status"] == "disabled":
        return "DISABLED", "GuardDuty not enabled"
    status = "ATTENTION REQUIRED" if results.get("findings", 0) > 0 else "OK"
    detail = f"{results.get('findings', 0)} findings today"
    return status, detail


def summarize_cloudwatch(results):
    if results.get("status") == "error":
        return "ERROR", results.get("error", "Unknown error")
    status = "ATTENTION REQUIRED" if results.get("count", 0) > 0 else "OK"
    detail = f"{results.get('count', 0)} alarm(s) in ALARM"
    return status, detail


def summarize_notifications(results):
    if results.get("status") == "error":
        return "ERROR", results.get("error", "Unknown error")
    status = "OK" if results.get("today_count", 0) == 0 else "NEW"
    detail = f"{results.get('today_count', 0)} new today; {results.get('total_managed', 0)} total managed"
    return status, detail


def summarize_backup(results):
    if results.get("status") == "error":
        return "ERROR", results.get("error", "Unknown error")
    issues = results.get("issues", [])
    status = "ATTENTION REQUIRED" if issues else "OK"
    detail = f"Jobs:{results.get('total_jobs', 0)} completed:{results.get('completed_jobs', 0)} failed:{results.get('failed_jobs', 0)}"
    return status, detail


def summarize_rds(results):
    if results.get("status") in ["error", "skipped"]:
        return results.get("status").upper(), results.get(
            "reason", results.get("error", "")
        )
    status = (
        "ATTENTION REQUIRED" if results.get("status") == "ATTENTION REQUIRED" else "OK"
    )
    instances = results.get("instances", {})
    warn_count = 0
    for data in instances.values():
        for m in data.get("metrics", {}).values():
            if m.get("status") == "warn":
                warn_count += 1
    detail = f"Instances:{len(instances)} warnings:{warn_count}"
    return status, detail


SUMMARY_MAP = {
    "health": summarize_health,
    "cost": summarize_cost,
    "guardduty": summarize_guardduty,
    "cloudwatch": summarize_cloudwatch,
    "notifications": summarize_notifications,
    "backup": summarize_backup,
    "daily-arbel": summarize_rds,
}


def _backup_problem_reason(res: dict) -> str:
    reasons = []
    if res.get("status") == "error":
        return f"check error: {res.get('error', 'unknown error')}"

    failed = int(res.get("failed_jobs", 0) or 0)
    expired = int(res.get("expired_jobs", 0) or 0)
    if failed > 0:
        reasons.append(f"{failed} job FAILED")
    if expired > 0:
        reasons.append(f"{expired} job EXPIRED")

    other_issues = [
        issue
        for issue in (res.get("issues") or [])
        if "failed" not in issue.lower() and "expired" not in issue.lower()
    ]
    if other_issues:
        reasons.append(other_issues[0])

    has_activity = (
        int(res.get("total_jobs", 0) or 0) > 0
        or any(v.get("recovery_points_24h", 0) > 0 for v in (res.get("vaults") or []))
        or int(res.get("rds_snapshots_24h", 0) or 0) > 0
    )
    if not has_activity:
        reasons.append("tidak ada aktivitas backup pada periode laporan")

    return "; ".join(reasons) if reasons else "perlu investigasi"


def summarize_backup_whatsapp(all_results):
    """Summarize backup status across accounts for WhatsApp/API consumers."""
    account_rows = []

    for profile, checks in all_results.items():
        res = checks.get("backup")
        if not res:
            continue

        display = BACKUP_DISPLAY_NAMES.get(profile, profile)
        account_id = get_account_id(profile)
        failed_jobs = int(res.get("failed_jobs", 0) or 0)
        expired_jobs = int(res.get("expired_jobs", 0) or 0)
        total_jobs = int(res.get("total_jobs", 0) or 0)
        issues = list(res.get("issues") or [])

        has_activity = (
            total_jobs > 0
            or any(
                v.get("recovery_points_24h", 0) > 0 for v in (res.get("vaults") or [])
            )
            or int(res.get("rds_snapshots_24h", 0) or 0) > 0
        )
        has_problem = (
            res.get("status") == "error"
            or failed_jobs > 0
            or expired_jobs > 0
            or len(issues) > 0
            or not has_activity
        )

        account_rows.append(
            {
                "profile": profile,
                "display_name": display,
                "account_id": account_id,
                "failed_jobs": failed_jobs,
                "expired_jobs": expired_jobs,
                "total_jobs": total_jobs,
                "problem": has_problem,
                "reason": _backup_problem_reason(res) if has_problem else "OK",
            }
        )

    total_accounts = len(account_rows)
    problem_accounts = [row for row in account_rows if row["problem"]]
    ok_accounts = [row for row in account_rows if not row["problem"]]
    all_success = total_accounts > 0 and len(problem_accounts) == 0

    return {
        "all_success": all_success,
        "total_accounts": total_accounts,
        "ok_accounts_count": len(ok_accounts),
        "problem_accounts_count": len(problem_accounts),
        "problem_accounts": problem_accounts,
        "accounts": account_rows,
    }


def build_whatsapp_backup(date_str, all_results):
    """Build single consolidated WhatsApp-ready backup report message."""
    summary = summarize_backup_whatsapp(all_results)
    if summary["total_accounts"] == 0:
        return "Tidak ada data backup yang relevan untuk dilaporkan."

    headline = (
        "Status Utama: ✅ Semua akun backup sukses"
        if summary["all_success"]
        else "Status Utama: ⚠️ Ada akun backup gagal/perlu perhatian"
    )

    lines = [
        "Selamat Pagi Team,",
        "Berikut laporan ringkas backup hari ini.",
        date_str,
        "",
        headline,
        (
            f"Ringkasan: total {summary['total_accounts']} akun | "
            f"sukses {summary['ok_accounts_count']} | "
            f"bermasalah {summary['problem_accounts_count']}"
        ),
    ]

    if summary["problem_accounts"]:
        lines.extend(["", "Akun Bermasalah:"])
        for row in summary["problem_accounts"]:
            lines.append(
                f"- ❌ {row['display_name']} - {row['account_id']} ({row['reason']})"
            )

    lines.extend(["", "Detail per akun:"])
    for row in summary["accounts"]:
        icon = "✅" if not row["problem"] else "❌"
        lines.append(
            f"- {icon} {row['display_name']} - {row['account_id']} | "
            f"jobs {row['total_jobs']} | failed {row['failed_jobs']} | expired {row['expired_jobs']}"
        )

    lines.extend(
        [
            "",
            "Catatan: Detail teknis per akun tetap tersedia di output detail checker.",
        ]
    )
    return "\n".join(lines)


def build_whatsapp_rds_compact(all_results):
    """Build compact WhatsApp-ready RDS report message."""

    now_jkt = datetime.now(timezone(timedelta(hours=7)))
    if 5 <= now_jkt.hour < 11:
        greeting = "Selamat Pagi"
    elif 11 <= now_jkt.hour < 15:
        greeting = "Selamat Siang"
    elif 15 <= now_jkt.hour < 18:
        greeting = "Selamat Sore"
    else:
        greeting = "Selamat Malam"

    time_str = now_jkt.strftime("%H:%M WIB")

    account_blocks = []
    warn_accounts = 0
    total_warn_metrics = 0
    action_queue = []

    for profile, checks in all_results.items():
        res = checks.get("daily-arbel")
        if not res or res.get("status") in ["skipped", "error"]:
            continue

        acct_id = res.get("account_id", get_account_id(profile))
        acct_name = res.get("account_name", profile)
        window_hours = res.get("window_hours", 12)

        account_warn = 0
        top_warn_lines = []
        instances = res.get("instances", {})
        for role, data in instances.items():
            metrics = data.get("metrics", {})
            for m, info in metrics.items():
                if info.get("status") == "warn":
                    account_warn += 1
                    total_warn_metrics += 1
                    top_warn_lines.append(
                        f"  • {role.capitalize()} - {info.get('message', m)}"
                    )

        if account_warn > 0:
            warn_accounts += 1
            status_line = f"⚠️ {acct_name} ({acct_id}) | {account_warn} warning"
            action_queue.append(f"- {acct_name}: cek metrik warning dan follow-up")
        else:
            status_line = f"✅ {acct_name} ({acct_id}) | normal"

        block_lines = [
            status_line,
            f"  ⏱️ Window: {window_hours}h",
        ]
        block_lines.extend(top_warn_lines[:3])
        if len(top_warn_lines) > 3:
            block_lines.append(f"  • ... {len(top_warn_lines) - 3} warning lain")
        account_blocks.append("\n".join(block_lines))

    if not account_blocks:
        return "Tidak ada data RDS untuk profil Aryanoble yang terkonfigurasi."

    lines = [
        f"{greeting} Team 👋",
        f"*Arbel RDS Snapshot* | {time_str}",
        "",
        f"📊 Summary: {warn_accounts} akun warning | {total_warn_metrics} metric warning",
        "",
        "🧾 Detail:",
        "\n\n".join(account_blocks),
    ]

    if action_queue:
        lines.extend(["", "🎯 Need Action:"])
        lines.extend(action_queue[:5])

    return "\n".join(lines)


def build_whatsapp_rds(all_results):
    """Build default client-facing WhatsApp-ready RDS report message."""
    return build_whatsapp_rds_client(all_results)


def build_whatsapp_rds_client(all_results):
    """Build formal client-facing WhatsApp-ready RDS report message."""

    now_jkt = datetime.now(timezone(timedelta(hours=7)))
    if 5 <= now_jkt.hour < 11:
        greeting = "Selamat Pagi"
        waktu = "Pagi"
    elif 11 <= now_jkt.hour < 15:
        greeting = "Selamat Siang"
        waktu = "Siang"
    elif 15 <= now_jkt.hour < 18:
        greeting = "Selamat Sore"
        waktu = "Sore"
    else:
        greeting = "Selamat Malam"
        waktu = "Malam"

    date_str = now_jkt.strftime("%d-%m-%Y")
    time_str = now_jkt.strftime("%H:%M WIB")

    messages = []
    for profile, checks in all_results.items():
        res = checks.get("daily-arbel")
        if not res or res.get("status") in ["skipped", "error"]:
            continue

        acct_id = res.get("account_id", get_account_id(profile))
        acct_name = res.get("account_name", profile)
        window_hours = res.get("window_hours", 12)

        lines = [f"{greeting} Team,"]
        lines.append(
            f"Berikut Daily report untuk akun id {acct_name} ({acct_id}) pada {waktu} ini (Data per {time_str}, monitoring {window_hours} jam terakhir)"
        )
        lines.extend([date_str, "", "Summary:"])

        # Delegate all rendering to checker's format_report for consistent output
        from src.checks.aryanoble.daily_arbel import DailyArbelChecker

        checker = DailyArbelChecker()
        body = checker.format_report(res)
        if body:
            messages.append(body)

    if not messages:
        return "Tidak ada data RDS untuk profil Aryanoble yang terkonfigurasi."

    sep = "\n" + ("-" * 70) + "\n\n"
    return sep.join(messages)


def build_whatsapp_alarm(all_results):
    """Build WhatsApp-ready alarm verification summary."""

    now_jkt = datetime.now(timezone(timedelta(hours=7)))
    if 5 <= now_jkt.hour < 11:
        greeting = "Selamat Pagi"
    elif 11 <= now_jkt.hour < 15:
        greeting = "Selamat Siang"
    elif 15 <= now_jkt.hour < 18:
        greeting = "Selamat Sore"
    else:
        greeting = "Selamat Malam"

    report_messages = []
    has_alarm_data = False

    for profile, checks in all_results.items():
        res = checks.get("alarm_verification")
        if not res or res.get("status") in ["skipped", "error"]:
            continue

        for alarm in res.get("alarms", []):
            has_alarm_data = True
            name = alarm.get("alarm_name", "N/A")
            action = alarm.get("recommended_action", "MONITOR")

            if action == "REPORT_NOW":
                msg = (alarm.get("message") or "").strip()
                if not msg:
                    threshold = alarm.get("threshold_text", "N/A")
                    msg = (
                        f"{greeting}, kami informasikan pada *{name}* sedang melewati "
                        f"threshold {threshold} sejak {alarm.get('breach_start_time', 'unknown')} "
                        f"(status: ongoing {alarm.get('ongoing_minutes', 0)} menit)."
                    )
                report_messages.append(msg)

    if not has_alarm_data:
        return "Tidak ada data alarm verification yang relevan."

    if report_messages:
        return "\n".join(report_messages)

    return "Tidak ada alarm yang perlu dilaporkan saat ini."


def build_whatsapp_budget(all_results):
    """Build budget threshold summary grouped by account."""
    grouped = []
    meta_period_utc = None
    meta_as_of_wib = None
    meta_mode = None
    for _, checks in all_results.items():
        res = checks.get("daily-budget")
        if not res or res.get("status") in ["error", "skipped"]:
            continue

        items = [
            x
            for x in res.get("items", [])
            if x.get("threshold_hits") or x.get("is_over_budget")
        ]
        if not items:
            continue

        grouped.append(
            {
                "account_id": res.get("account_id", ""),
                "account_name": res.get("account_name", res.get("profile", "")),
                "items": items,
                "max_percent": max(x.get("percent", 0) for x in items),
            }
        )

        if meta_period_utc is None:
            meta_period_utc = res.get("period_utc_date")
            meta_as_of_wib = res.get("as_of_wib")
            meta_mode = res.get("data_mode")

    if not grouped:
        return "Tidak ada budget melewati alert threshold."

    grouped.sort(key=lambda x: x["max_percent"], reverse=True)
    lines = []
    if meta_period_utc or meta_as_of_wib:
        mode_label = meta_mode or "snapshot"
        lines.append(
            f"Data: {meta_period_utc or 'N/A'} UTC | As of: {meta_as_of_wib or 'N/A'} | Mode: {mode_label}"
        )
        lines.append("")
    for idx, entry in enumerate(grouped, start=1):
        lines.append(f"{idx}) Account {entry['account_id']} - {entry['account_name']}")
        for it in entry["items"]:
            line = (
                f"- {it['budget_name']}: ${it['actual']:.2f} / ${it['limit']:.2f} "
                f"({it['percent']:.2f}%)"
            )
            if it.get("is_over_budget"):
                line += f" -> Over ${it['over_amount']:.2f}"
            else:
                hits = ", ".join(f"{h:.0f}%" for h in it.get("threshold_hits", []))
                line += f" -> Exceeded alert threshold ({hits})"
            lines.append(line)
    return "\n".join(lines)


def generate_whatsapp_message(all_results):
    """Generate a WhatsApp-ready text focusing on Backup and RDS for Aryanoble."""
    now_jkt = datetime.now(timezone(timedelta(hours=7)))
    lines = [
        "Selamat Pagi Team,",
        f"Laporan daily Aryanoble {now_jkt:%d-%m-%Y}",
        "",
    ]

    # Backup section
    backup_lines = []
    for profile, checks in all_results.items():
        backup = checks.get("backup")
        if not backup:
            continue
        if backup.get("status") == "error":
            backup_lines.append(f"- {profile}: ERROR {backup.get('error', '')}")
            continue
        if backup.get("issues"):
            issues = "; ".join(backup.get("issues", []))
            backup_lines.append(f"- {profile}: Attention ({issues})")
        else:
            backup_lines.append(
                f"- {profile}: OK (jobs {backup.get('total_jobs', 0)} / failed {backup.get('failed_jobs', 0)})"
            )

    if backup_lines:
        lines.append("Backup:")
        lines.extend(backup_lines)
        lines.append("")

    # RDS section
    rds_lines = []
    for profile, checks in all_results.items():
        rds = checks.get("daily-arbel")
        if not rds or rds.get("status") == "skipped":
            continue
        if rds.get("status") == "error":
            rds_lines.append(f"- {profile}: ERROR {rds.get('error', '')}")
            continue
        warn = 0
        for data in rds.get("instances", {}).values():
            for m in data.get("metrics", {}).values():
                if m.get("status") == "warn":
                    warn += 1
        if warn:
            rds_lines.append(f"- {profile}: Attention ({warn} metric warning)")
        else:
            rds_lines.append(f"- {profile}: OK (RDS metrics normal)")

    if rds_lines:
        lines.append("RDS:")
        lines.extend(rds_lines)
        lines.append("")

    if not backup_lines and not rds_lines:
        lines.append("Tidak ada data Backup/RDS yang relevan untuk Aryanoble.")

    lines.append("Terima kasih.")
    return "\n".join(lines)


def build_whatsapp_backup_aryanoble(date_str, all_results):
    """Build Aryanoble-specific WhatsApp backup report with Completed/Failed/Expired sections."""

    # Exclude arbel-master from reporting
    EXCLUDED_PROFILES = ["arbel-master"]
    filtered_results = {
        k: v for k, v in all_results.items() if k not in EXCLUDED_PROFILES
    }

    # Get display names
    display_names = BACKUP_DISPLAY_NAMES

    # Categorize accounts
    completed_accounts = []
    failed_accounts = []
    expired_accounts = []

    for profile, checks in filtered_results.items():
        backup_result = checks.get("backup")
        if not backup_result:
            continue

        display_name = display_names.get(profile, profile)
        account_id = backup_result.get("account_id", "")
        failed_jobs = backup_result.get("failed_jobs", 0)
        expired_jobs = backup_result.get("expired_jobs", 0)
        completed_jobs = backup_result.get("completed_jobs", 0)
        issues = backup_result.get("issues", [])

        # Check for vault issues (no activity or errors)
        has_vault_issues = any("vault" in issue.lower() for issue in issues)

        # Categorize account
        if failed_jobs > 0 or has_vault_issues:
            failed_accounts.append(
                {
                    "display_name": display_name,
                    "account_id": account_id,
                    "profile": profile,
                    "backup_result": backup_result,
                }
            )

        if expired_jobs > 0:
            expired_accounts.append(
                {
                    "display_name": display_name,
                    "account_id": account_id,
                    "profile": profile,
                    "backup_result": backup_result,
                }
            )

        # Only add to completed if no failures, no expired, and has activity
        if (
            failed_jobs == 0
            and expired_jobs == 0
            and not has_vault_issues
            and (
                completed_jobs > 0
                or any(
                    "recovery_points_24h" in str(v)
                    for v in backup_result.get("vaults", [])
                )
            )
        ):
            completed_accounts.append(
                {"display_name": display_name, "account_id": account_id}
            )

    # Build report
    lines = [
        "Selamat Pagi Team,",
        "Berikut report untuk AryaNoble Backup pada hari ini",
        date_str,
        "",
        "Completed:",
    ]

    if completed_accounts:
        for acc in completed_accounts:
            lines.append(f"- {acc['display_name']} - {acc['account_id']}")
    else:
        lines.append("- (tidak ada)")

    lines.extend(["", "Failed:"])

    if failed_accounts:
        for acc in failed_accounts:
            lines.append(f"- {acc['display_name']} - {acc['account_id']}")

            # Add job details for failed jobs
            job_details = acc["backup_result"].get("job_details", [])
            failed_job_details = [j for j in job_details if j.get("state") == "FAILED"]

            for i, job in enumerate(failed_job_details[:10], 1):  # Limit to 10 details
                lines.append(f"  Detail {i}:")
                lines.append(f"    Resource: {job.get('resource_label', 'N/A')}")

                # Format timestamp
                created_wib = job.get("created_wib")
                if created_wib:
                    time_str = created_wib.strftime("%d-%m-%Y %H:%M WIB")
                else:
                    time_str = "N/A"
                lines.append(f"    Time: {time_str}")
                lines.append(f"    Reason: {job.get('reason', 'No reason provided')}")
    else:
        lines.append("- (tidak ada)")

    lines.extend(["", "Expired:"])

    if expired_accounts:
        for acc in expired_accounts:
            lines.append(f"- {acc['display_name']} - {acc['account_id']}")

            # Add job details for expired jobs
            job_details = acc["backup_result"].get("job_details", [])
            expired_job_details = [
                j for j in job_details if j.get("state") == "EXPIRED"
            ]

            for i, job in enumerate(expired_job_details[:10], 1):  # Limit to 10 details
                lines.append(f"  Detail {i}:")
                lines.append(f"    Resource: {job.get('resource_label', 'N/A')}")

                # Format timestamp
                created_wib = job.get("created_wib")
                if created_wib:
                    time_str = created_wib.strftime("%d-%m-%Y %H:%M WIB")
                else:
                    time_str = "N/A"
                lines.append(f"    Time: {time_str}")
                lines.append(f"    Reason: {job.get('reason', 'Backup job expired')}")
    else:
        lines.append("- (tidak ada)")

    return "\n".join(lines)
