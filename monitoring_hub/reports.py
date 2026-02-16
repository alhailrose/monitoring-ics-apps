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


def build_whatsapp_backup(date_str, all_results):
    """Build WhatsApp-ready backup report message."""
    completed_lines = []
    failed_lines = []
    expired_lines = []
    vault_gap_lines = []
    nobackup_lines = []

    for profile, checks in all_results.items():
        res = checks.get("backup")
        if not res or res.get("status") == "error":
            continue

        display = BACKUP_DISPLAY_NAMES.get(profile, profile)
        acct = get_account_id(profile)
        has_activity = (
            res.get("total_jobs", 0) > 0
            or any(v.get("recovery_points_24h", 0) > 0 for v in res.get("vaults", []))
            or res.get("rds_snapshots_24h", 0) > 0
        )

        if not has_activity:
            nobackup_lines.append(
                f"- {display} - {acct} (tidak ada backup pada periode)"
            )
            continue

        missing_vaults = [
            v
            for v in res.get("vaults", [])
            if v.get("recovery_points_24h", 0) == 0 and not v.get("error")
        ]
        if missing_vaults:
            vault_gap_lines.append(
                f"- {display} - {acct} vault gap: {len(missing_vaults)} vault tanpa RP 24h"
            )

        issues = res.get("issues", [])
        failed = res.get("failed_jobs", 0)
        expired = res.get("expired_jobs", 0)

        if not issues:
            completed_lines.append(f"- {display} - {acct}")
        else:
            # Get failed/expired job details
            job_details = res.get("job_details", [])
            failed_jobs = [j for j in job_details if j.get("state") == "FAILED"]
            expired_jobs = [j for j in job_details if j.get("state") == "EXPIRED"]

            if failed_jobs:
                for job in failed_jobs:
                    ts_wib = job.get("created_wib")
                    ts_str = (
                        ts_wib.strftime("%d-%m-%Y %H:%M WIB")
                        if hasattr(ts_wib, "strftime")
                        else str(ts_wib)
                    )
                    reason = job.get("reason", "No reason")
                    resource = job.get("resource_label", "N/A")
                    failed_lines.append(f"- {display} - {acct}")
                    failed_lines.append(f"  Resource: {resource}")
                    failed_lines.append(f"  Time: {ts_str}")
                    failed_lines.append(f"  Reason: {reason}")

            if expired_jobs:
                for job in expired_jobs:
                    ts_wib = job.get("created_wib")
                    ts_str = (
                        ts_wib.strftime("%d-%m-%Y %H:%M WIB")
                        if hasattr(ts_wib, "strftime")
                        else str(ts_wib)
                    )
                    reason = job.get("reason", "No reason")
                    resource = job.get("resource_label", "N/A")
                    expired_lines.append(f"- {display} - {acct}")
                    expired_lines.append(f"  Resource: {resource}")
                    expired_lines.append(f"  Time: {ts_str}")
                    expired_lines.append(f"  Reason: {reason}")

            # Other issues (vault gaps, etc)
            for i in issues:
                if "failed" in i or "expired" in i:
                    continue
                failed_lines.append(f"- {display} - {acct} => {i}")

    completed_block = (
        "\r\n".join(completed_lines) if completed_lines else "- (tidak ada)"
    )
    failed_block = "\r\n".join(failed_lines) if failed_lines else "- (tidak ada)"
    expired_block = "\r\n".join(expired_lines) if expired_lines else "- (tidak ada)"

    return (
        "Selamat Pagi Team,\r\n"
        "Berikut report untuk AryaNoble Backup pada hari ini\r\n"
        f"{date_str}\r\n\r\n"
        "Completed:\r\n"
        f"{completed_block}\r\n\r\n"
        "Failed:\r\n"
        f"{failed_block}\r\n\r\n"
        "Expired:\r\n"
        f"{expired_block}\r\n"
    ).strip()


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
            for m in [
                "ACUUtilization",
                "CPUUtilization",
                "FreeableMemory",
                "DatabaseConnections",
            ]:
                info = metrics.get(m, {})
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

        instances = res.get("instances", {})
        for role, data in instances.items():
            lines.append("")
            lines.append(f"{role.capitalize()}:")
            metrics = data.get("metrics", {})
            for m in [
                "ACUUtilization",
                "CPUUtilization",
                "FreeableMemory",
                "DatabaseConnections",
            ]:
                info = metrics.get(m, {})
                msg = info.get("message", f"{m}: Data tidak tersedia")
                lines.append(f"* {msg}")

        messages.append("\n".join(lines))

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

    time_str = now_jkt.strftime("%H:%M WIB")

    report_now = []
    monitor = []
    recovered = []
    not_found = []

    for profile, checks in all_results.items():
        res = checks.get("alarm_verification")
        if not res or res.get("status") in ["skipped", "error"]:
            continue

        acct = res.get("account_id", get_account_id(profile))
        for alarm in res.get("alarms", []):
            name = alarm.get("alarm_name", "N/A")
            action = alarm.get("recommended_action", "MONITOR")
            if alarm.get("status") == "not-found":
                not_found.append(f"- {name} ({profile}/{acct})")
                continue

            if action == "REPORT_NOW":
                report_now.append(
                    f"- {name} ({profile}) | {alarm.get('ongoing_minutes', 0)}m ongoing"
                )
            elif action == "MONITOR":
                monitor.append(
                    f"- {name} ({profile}) | {alarm.get('ongoing_minutes', 0)}m ongoing"
                )
            elif action == "NO_REPORT_RECOVERED":
                recovered.append(
                    f"- {name} ({profile}) | recovered {alarm.get('breach_duration_minutes', 0)}m"
                )

    lines = [
        f"{greeting} Team 👋",
        f"*Arbel Alarm Verification* | {time_str}",
        "",
        f"📊 Summary: REPORT_NOW={len(report_now)} | MONITOR={len(monitor)} | RECOVERED={len(recovered)}",
    ]

    if report_now:
        lines.extend(["", "🚨 REPORT NOW:"])
        lines.extend(report_now[:8])
    if monitor:
        lines.extend(["", "⏳ MONITOR:"])
        lines.extend(monitor[:8])
    if recovered:
        lines.extend(["", "✅ RECOVERED (no report):"])
        lines.extend(recovered[:8])
    if not_found:
        lines.extend(["", "❓ NOT FOUND:"])
        lines.extend(not_found[:5])

    if not report_now and not monitor and not recovered and not not_found:
        return "Tidak ada data alarm verification yang relevan."

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
