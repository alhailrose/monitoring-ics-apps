"""
Check runner functions for AWS Monitoring Hub.
Includes parallel execution with progress bars and detailed text output.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Optional

from botocore.exceptions import BotoCoreError, ClientError
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)
from rich import box

from .config import (
    AVAILABLE_CHECKS,
    ALL_MODE_CHECKS,
    ALL_MODE_CHECKS_NO_BACKUP_RDS,
    DEFAULT_WORKERS,
)
from .utils import get_account_id
from .reports import (
    build_whatsapp_backup,
    build_whatsapp_rds,
    build_whatsapp_alarm,
    build_whatsapp_budget,
)
from .ui import (
    console,
    print_check_header,
    print_group_header,
    ICONS,
)
from src.integrations.slack.notifier import send_report_to_slack


def run_individual_check(
    check_name: str, profile: str, region: str, send_slack: bool = False
):
    """Run individual check with detailed output and beautiful UI."""
    if check_name not in AVAILABLE_CHECKS:
        console.print(
            f"[bold red]{ICONS['error']} ERROR[/bold red]: Unknown check '{check_name}'"
        )
        console.print(f"Available checks: {', '.join(AVAILABLE_CHECKS.keys())}")
        return

    account_id = get_account_id(profile)
    checker_class = AVAILABLE_CHECKS[check_name]
    checker = checker_class(region=region)

    # Beautiful header
    print_check_header(check_name, profile, account_id, region)

    # Run check with spinner
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]Running check...[/bold cyan]"),
        transient=True,
        console=console,
    ) as progress:
        progress.add_task("checking", total=None)
        try:
            results = checker.check(profile, account_id)
            report = checker.format_report(results)
        except (BotoCoreError, ClientError) as exc:
            console.print(
                f"\n[bold red]{ICONS['error']} ERROR[/bold red]: Failed to run {check_name}: {exc}"
            )
            return
        except Exception as exc:
            console.print(
                f"\n[bold red]{ICONS['error']} ERROR[/bold red]: Unexpected failure: {exc}"
            )
            return

    console.print()
    console.print(report)

    if send_slack:
        sent, reason = send_report_to_slack(check_name, report, client_key=profile)
        if sent:
            console.print(f"\n[green]{ICONS['check']} Slack report sent[/green]")
        else:
            console.print(f"\n[yellow]{ICONS['info']} Slack skipped[/yellow]: {reason}")


def _check_single_profile(
    check_name: str, profile: str, region: str, check_kwargs: Optional[dict] = None
) -> dict:
    """Run a single check on a profile. Used for parallel execution."""
    account_id = get_account_id(profile)
    checker_class = AVAILABLE_CHECKS[check_name]
    checker = checker_class(region=region, **(check_kwargs or {}))

    try:
        results = checker.check(profile, account_id)
    except (BotoCoreError, ClientError) as exc:
        results = {"status": "error", "error": str(exc)}
    except Exception as exc:
        results = {"status": "error", "error": str(exc)}

    return results


def _check_all_for_profile(profile: str, region: str, checks: dict) -> dict:
    """Run all checks for a single profile. Used for parallel execution."""
    profile_results = {}

    for check_name, checker_class in checks.items():
        checker = checker_class(region=region)
        account_id = get_account_id(profile)
        try:
            results = checker.check(profile, account_id)
        except (BotoCoreError, ClientError) as exc:
            results = {"status": "error", "error": str(exc)}
        except Exception as exc:
            results = {"status": "error", "error": str(exc)}
        profile_results[check_name] = results

    return profile_results


def run_group_specific(
    check_name: str,
    profiles: list,
    region: str,
    group_name: Optional[str] = None,
    workers: int = DEFAULT_WORKERS,
    check_kwargs: Optional[dict] = None,
    send_slack: bool = False,
):
    """Run a specific check across multiple profiles with parallel execution."""

    # Beautiful header
    print_group_header(check_name, len(profiles), group_name, region)

    # Time info for backup checks
    if check_name == "backup":
        now_utc = datetime.now(timezone.utc)
        since_utc = now_utc - timedelta(hours=24)
        now_jkt = now_utc.astimezone(timezone(timedelta(hours=7)))
        since_jkt = since_utc.astimezone(timezone(timedelta(hours=7)))
        console.print(
            f"[bold]Periode[/bold] : 24 jam terakhir (sejak: {since_jkt:%Y-%m-%d %H:%M:%S %Z})"
        )
        console.print(f"[bold]Time   [/bold] : {now_jkt:%Y-%m-%d %H:%M:%S %Z}\n")

    all_results = {}

    # Parallel execution with progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}[/bold cyan]"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        TextColumn("[dim]{task.fields[current]}[/dim]"),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"Checking {len(profiles)} profiles...", total=len(profiles), current=""
        )

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    _check_single_profile, check_name, profile, region, check_kwargs
                ): profile
                for profile in profiles
            }

            for future in as_completed(futures):
                profile = futures[future]
                try:
                    results = future.result()
                except Exception as exc:
                    results = {"status": "error", "error": str(exc)}

                all_results[profile] = {check_name: results}
                progress.update(task, advance=1, current=profile)

    console.print()

    # For non-backup/rds checks, print each profile's report
    if check_name not in ["backup", "daily-arbel"]:
        checker_class = AVAILABLE_CHECKS[check_name]
        checker = checker_class(region=region, **(check_kwargs or {}))
        for profile in profiles:
            res = all_results.get(profile, {}).get(check_name, {})
            report = checker.format_report(res)
            print(f"\n[{profile}]")
            print(report)
            print("")

    # WhatsApp message and detailed output for backup
    if check_name == "backup":
        date_str = datetime.now(timezone(timedelta(hours=7))).strftime("%d-%m-%Y")
        whatsapp = build_whatsapp_backup(date_str, all_results)

        # Detailed per-account view
        print("\n" + "=" * 70)
        print("DETAIL PER ACCOUNT (BACKUP, 24H WINDOW)")
        print("=" * 70)

        for profile in profiles:
            res = all_results.get(profile, {}).get("backup")
            if not res:
                continue
            acct = res.get("account_id", get_account_id(profile))

            print(
                f"\n== {profile} | Account: {acct} | Region: {res.get('region', region)} =="
            )
            print(
                f"Checked at: {res.get('checked_at_utc')} | Window start: {res.get('window_start_utc')}"
            )
            print(
                f"Jobs (24h): total {res.get('total_jobs', 0)} | completed {res.get('completed_jobs', 0)} | failed {res.get('failed_jobs', 0)} | expired {res.get('expired_jobs', 0)}"
            )

            jobs = res.get("job_details", [])
            if jobs:
                print("AWS BACKUP JOBS (24h, max 20 baris):")
                header = f"{'JobID':36}  {'Status':10} {'Type':8} {'Created (WIB)':20} {'Resource':22} {'ResName':22} {'Reason':30}"
                print(header)
                print("-" * len(header))
                for j in jobs[:20]:
                    ts = j.get("created_wib") or j.get("created")
                    ts_str = (
                        ts.strftime("%Y-%m-%d %H:%M")
                        if hasattr(ts, "strftime")
                        else str(ts)
                    )
                    job_id = (j.get("job_id", "") or "")[:36]
                    status = (j.get("state", "") or "")[:10]
                    rtype = (j.get("type", "") or "")[:8]
                    res_label = (j.get("resource_label", "") or "")[:22]
                    res_full = (j.get("resource", "") or "")[:22]
                    reason = (j.get("reason", "") or "")[:30]
                    print(
                        f"{job_id:36}  {status:10} {rtype:8} {ts_str:20} {res_label:22} {res_full:22} {reason:30}"
                    )
            else:
                print("AWS BACKUP JOBS: (none)")

            plans = res.get("backup_plans", [])
            if plans:
                print("Backup plans (maks 10):")
                for p in plans[:10]:
                    print(f"  - {p}")

            vaults = res.get("vaults", [])
            if vaults:
                print("Vaults:")
                for v in vaults:
                    if v.get("error"):
                        print(f"  - {v['vault_name']}: ERROR {v['error']}")
                    else:
                        print(
                            f"  - {v['vault_name']}: {v.get('recovery_points_24h', 0)} RP 24h; total {v.get('total_recovery_points', 0)}"
                        )
            print("")

        print("\n" + "=" * 70)
        print("WHATSAPP MESSAGE (READY TO SEND)")
        print("=" * 70)
        print("--backup")
        print(whatsapp)

    elif check_name == "daily-arbel":
        whatsapp = build_whatsapp_rds(all_results)

        print("\n" + "=" * 70)
        print("WHATSAPP MESSAGE (READY TO SEND)")
        print("=" * 70)
        print("--rds")
        print(whatsapp)

    elif check_name == "alarm_verification":
        whatsapp = build_whatsapp_alarm(all_results)

        print("\n" + "=" * 70)
        print("WHATSAPP MESSAGE (READY TO SEND)")
        print("=" * 70)
        print("--alarm")
        print(whatsapp)

    elif check_name == "daily-budget":
        whatsapp = build_whatsapp_budget(all_results)

        print("\n" + "=" * 70)
        print("WHATSAPP MESSAGE (READY TO SEND)")
        print("=" * 70)
        print("--budget")
        print(whatsapp)

    else:
        whatsapp = None

    if send_slack:
        checker_class = AVAILABLE_CHECKS.get(check_name)
        sent_count = 0
        skipped_count = 0

        if checker_class is not None:
            checker = checker_class(region=region, **(check_kwargs or {}))
            for profile, checks in all_results.items():
                result = checks.get(check_name)
                if not result or result.get("status") in ["error", "skipped"]:
                    continue

                text_to_send = checker.format_report(result)
                sent, reason = send_report_to_slack(
                    check_name,
                    text_to_send,
                    client_key=profile,
                )
                if sent:
                    sent_count += 1
                else:
                    skipped_count += 1
                    console.print(
                        f"[yellow]{ICONS['info']} Slack skipped for {profile}[/yellow]: {reason}"
                    )

        if sent_count > 0:
            console.print(
                f"\n[green]{ICONS['check']} Slack report sent[/green] to {sent_count} client route(s)"
            )
        elif skipped_count > 0:
            console.print(
                f"\n[yellow]{ICONS['info']} No Slack report delivered[/yellow] ({skipped_count} skipped)"
            )


def run_all_checks(
    profiles: list,
    region: str,
    group_name: Optional[str] = None,
    workers: int = DEFAULT_WORKERS,
    exclude_backup_rds: bool = True,
):
    """Run all checks with parallel execution and detailed text output."""

    checks = ALL_MODE_CHECKS_NO_BACKUP_RDS if exclude_backup_rds else ALL_MODE_CHECKS

    # Header
    console.print(
        Panel(
            f"[bold]{len(profiles)}[/bold] profiles  {ICONS['dot']}  "
            f"Region: [green]{region}[/green]  {ICONS['dot']}  "
            f"Group: [cyan]{group_name or '-'}[/cyan]  {ICONS['dot']}  "
            f"Workers: [yellow]{workers}[/yellow]",
            title=f"[bold]{ICONS['all']} All Checks[/bold]",
            border_style="cyan",
            box=box.DOUBLE,
            padding=(1, 2),
        )
    )

    all_results = {}
    total_anomalies = 0
    total_findings = 0
    total_alarms = 0
    total_new_notifications = 0
    check_errors = []
    clean_accounts = []
    guardduty_disabled = []
    errors_by_check = {name: [] for name in checks.keys()}

    # Parallel execution with progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}[/bold cyan]"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        TextColumn("[dim]{task.fields[current]}[/dim]"),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"Checking {len(profiles)} profiles ({len(checks)} checks each)...",
            total=len(profiles),
            current="",
        )

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    _check_all_for_profile, profile, region, checks
                ): profile
                for profile in profiles
            }

            for future in as_completed(futures):
                profile = futures[future]
                try:
                    profile_results = future.result()
                except Exception as exc:
                    profile_results = {
                        name: {"status": "error", "error": str(exc)} for name in checks
                    }

                all_results[profile] = profile_results
                progress.update(task, advance=1, current=profile)

                # Track issues
                has_issue = False
                for chk_name, results in profile_results.items():
                    if results.get("status") == "error":
                        check_errors.append(
                            (profile, chk_name, results.get("error", "Unknown error"))
                        )
                        errors_by_check[chk_name].append(
                            (profile, results.get("error", "Unknown error"))
                        )
                        has_issue = True
                    if chk_name == "cost":
                        anomalies = int(results.get("total_anomalies", 0) or 0)
                        if anomalies > 0:
                            total_anomalies += anomalies
                            has_issue = True
                    elif chk_name == "guardduty":
                        if results.get("status") == "disabled":
                            guardduty_disabled.append(profile)
                        else:
                            findings = int(results.get("findings", 0) or 0)
                            if findings > 0:
                                total_findings += findings
                                has_issue = True
                    elif chk_name == "cloudwatch":
                        alarms = int(results.get("count", 0) or 0)
                        if alarms > 0:
                            total_alarms += alarms
                            has_issue = True
                    elif chk_name == "notifications":
                        new_notif = int(results.get("today_count", 0) or 0)
                        if new_notif > 0:
                            total_new_notifications += new_notif
                            has_issue = True

                if not has_issue:
                    clean_accounts.append(profile)

    console.print()

    include_backup_rds = "backup" in checks or "daily-arbel" in checks

    if include_backup_rds:
        _print_detailed_report(
            profiles=profiles,
            all_results=all_results,
            total_anomalies=total_anomalies,
            total_findings=total_findings,
            total_alarms=total_alarms,
            check_errors=check_errors,
            clean_accounts=clean_accounts,
            guardduty_disabled=guardduty_disabled,
            errors_by_check=errors_by_check,
            region=region,
            group_name=group_name,
        )
    else:
        _print_simple_report(
            profiles=profiles,
            all_results=all_results,
            total_anomalies=total_anomalies,
            total_findings=total_findings,
            total_alarms=total_alarms,
            check_errors=check_errors,
            guardduty_disabled=guardduty_disabled,
            region=region,
        )


def _print_detailed_report(
    profiles,
    all_results,
    total_anomalies,
    total_findings,
    total_alarms,
    check_errors,
    clean_accounts,
    guardduty_disabled,
    errors_by_check,
    region,
    group_name,
):
    """Print detailed text report for copy-paste reporting."""

    now = datetime.now()
    date_str = now.strftime("%B %d, %Y")
    time_str = now.strftime("%H:%M WIB")

    lines = []

    # Header
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

    # Executive Summary
    lines.append("-" * 70)
    lines.append("EXECUTIVE SUMMARY")
    lines.append("-" * 70)

    summary_text = f"Security assessment completed across {len(profiles)} AWS accounts."
    if check_errors:
        summary_text += f" {len(check_errors)} check error(s) encountered; see CHECK ERRORS section."
    if (
        total_anomalies == 0
        and total_findings == 0
        and total_alarms == 0
        and not check_errors
    ):
        summary_text += (
            " No new security incidents detected. All systems operating normally."
        )
    else:
        issues = []
        if check_errors:
            issues.append(f"{len(check_errors)} check errors")
        if total_anomalies > 0:
            issues.append(f"{total_anomalies} cost anomalies")
        if total_findings > 0:
            issues.append(f"{total_findings} new security findings")
        if total_alarms > 0:
            issues.append(f"{total_alarms} infrastructure alerts")
        summary_text += f" {' and '.join(issues)} detected requiring attention."
    lines.append(summary_text)
    lines.append("")

    # Assessment Results
    lines.append("-" * 70)
    lines.append("ASSESSMENT RESULTS")
    lines.append("-" * 70)

    # Cost Anomalies Section
    lines.append("")
    lines.append("COST ANOMALIES")
    if errors_by_check.get("cost"):
        lines.append("Status: ERROR - Cost Anomaly check failed")
        lines.append("Errors:")
        for prof, err in errors_by_check["cost"][:5]:
            lines.append(f"  * {prof}: {err}")
        if len(errors_by_check["cost"]) > 5:
            lines.append(f"  ... and {len(errors_by_check['cost']) - 5} more")
    elif total_anomalies == 0:
        lines.append("Status: CLEAR - No cost anomalies detected")
    else:
        lines.append(
            f"Status: ATTENTION REQUIRED - {total_anomalies} anomalies detected"
        )
        lines.append("")
        lines.append("Detected Anomalies:")
        for profile, results in all_results.items():
            cost_data = results.get("cost", {})
            if cost_data.get("total_anomalies", 0) > 0:
                account_id = get_account_id(profile)
                lines.append(
                    f"  * {profile} ({account_id}): {cost_data['total_anomalies']} anomalies"
                )
                for anomaly in cost_data.get("anomalies", [])[:3]:
                    impact = anomaly.get("Impact", {}).get("TotalImpact", "0")
                    anomaly_start = anomaly.get("AnomalyStartDate", "N/A")
                    anomaly_end = anomaly.get("AnomalyEndDate", "N/A")
                    lines.append(f"    - Monitor: {anomaly.get('MonitorName', 'N/A')}")
                    lines.append(f"    - Impact: ${impact}")
                    lines.append(f"    - Date: {anomaly_start} to {anomaly_end}")

                    root_causes = anomaly.get("RootCauses", [])
                    if root_causes:
                        services = list(
                            set([rc.get("Service", "N/A") for rc in root_causes])
                        )
                        lines.append(
                            f"    - Affected Services: {', '.join(services[:3])}"
                        )
                        if len(services) > 3:
                            lines.append(
                                f"      ... and {len(services) - 3} more services"
                            )
                        top_cause = root_causes[0]
                        lines.append(
                            f"    - Top Root Cause: {top_cause.get('Service', 'N/A')} - {top_cause.get('UsageType', 'N/A')}"
                        )

    # GuardDuty Section
    lines.append("")
    lines.append("GUARDDUTY FINDINGS")
    if errors_by_check.get("guardduty"):
        lines.append("Status: ERROR - GuardDuty check failed")
        lines.append("Errors:")
        for prof, err in errors_by_check["guardduty"][:5]:
            lines.append(f"  * {prof}: {err}")
        if len(errors_by_check["guardduty"]) > 5:
            lines.append(f"  ... and {len(errors_by_check['guardduty']) - 5} more")
    elif total_findings > 0 or guardduty_disabled:
        if total_findings > 0:
            lines.append(
                f"Status: ATTENTION REQUIRED - {total_findings} new findings detected"
            )
            lines.append("")
            lines.append("Current Findings:")
            for profile, results in all_results.items():
                gd_data = results.get("guardduty", {})
                if gd_data.get("findings", 0) > 0:
                    account_id = get_account_id(profile)
                    lines.append(
                        f"  * {profile} ({account_id}): {gd_data['findings']} findings"
                    )
                    for detail in gd_data.get("details", [])[:3]:
                        lines.append(f"    - Type: {detail.get('type', 'N/A')}")
                        lines.append(f"    - Severity: {detail.get('severity', 'N/A')}")
                        lines.append(f"    - Date: {detail.get('updated', 'N/A')}")

        if guardduty_disabled:
            if total_findings > 0:
                lines.append("")
            lines.append("GuardDuty NOT ENABLED:")
            for profile in guardduty_disabled:
                account_id = get_account_id(profile)
                lines.append(f"  * {profile} ({account_id})")
    else:
        lines.append("Status: CLEAR - No new security findings detected")

    # CloudWatch Section
    lines.append("")
    lines.append("CLOUDWATCH ALARMS")
    if errors_by_check.get("cloudwatch"):
        lines.append("Status: ERROR - CloudWatch check failed")
        lines.append("Errors:")
        for prof, err in errors_by_check["cloudwatch"][:5]:
            lines.append(f"  * {prof}: {err}")
        if len(errors_by_check["cloudwatch"]) > 5:
            lines.append(f"  ... and {len(errors_by_check['cloudwatch']) - 5} more")
    elif total_alarms == 0:
        lines.append("Status: All monitoring systems normal")
    else:
        lines.append(f"Status: {total_alarms} alarms in ALARM state")
        lines.append("")
        lines.append("Active Alarms:")
        for profile, results in all_results.items():
            cw_data = results.get("cloudwatch", {})
            if cw_data.get("count", 0) > 0:
                account_id = get_account_id(profile)
                lines.append(
                    f"  * {profile} ({account_id}): {cw_data['count']} active alarms"
                )
                for detail in cw_data.get("details", [])[:3]:
                    lines.append(f"    - Alarm: {detail.get('name', 'N/A')}")
                    lines.append(f"    - Reason: {detail.get('reason', 'N/A')}")
                    lines.append(f"    - Date: {detail.get('updated', 'N/A')}")

    # Notification Center Section
    notif_data = None
    all_notif_events = []
    total_today = 0
    total_managed_all = 0

    for profile, results in all_results.items():
        if "notifications" in results:
            notif_result = results["notifications"]
            if notif_result.get("status") == "success":
                if notif_data is None:
                    notif_data = notif_result
                total_today += notif_result.get("today_count", 0)
                total_managed_all += notif_result.get("total_managed", 0)
                all_notif_events.extend(notif_result.get("all_events", []))

    lines.append("")
    lines.append("NOTIFICATION CENTER")
    if errors_by_check.get("notifications"):
        lines.append("Status: ERROR - Notification Center check failed")
        lines.append("Errors:")
        for prof, err in errors_by_check["notifications"][:5]:
            lines.append(f"  * {prof}: {err}")
        if len(errors_by_check["notifications"]) > 5:
            lines.append(f"  ... and {len(errors_by_check['notifications']) - 5} more")
    elif notif_data:
        if total_today == 0:
            lines.append(
                f"Status: No new notifications today ({total_managed_all} existing available)"
            )
        else:
            lines.append(f"Status: {total_today} new notifications detected today")
            lines.append("")
            lines.append("Today's Notifications:")
            for event in notif_data.get("today_events", [])[:3]:
                notif_event = event.get("notificationEvent", {})
                event_type = notif_event.get("sourceEventMetadata", {}).get(
                    "eventType", "N/A"
                )
                headline = notif_event.get("messageComponents", {}).get(
                    "headline", "N/A"
                )
                lines.append(f"  * Event Type: {event_type}")
                lines.append(f"    Description: {headline}")

        # Show all existing notifications from all accounts
        lines.append("")
        lines.append(
            f"[DEBUG] all_notif_events length: {len(all_notif_events)}, total_managed_all: {total_managed_all}"
        )
        if len(all_notif_events) > 0:
            # Sort by creation time (newest first)
            sorted_events = sorted(
                all_notif_events, key=lambda x: x.get("creationTime", ""), reverse=True
            )
            lines.append("")
            lines.append(f"All Notifications ({len(sorted_events)} total):")
            for event in sorted_events[:5]:
                notif_event = event.get("notificationEvent", {})
                event_type = notif_event.get("sourceEventMetadata", {}).get(
                    "eventType", "N/A"
                )
                headline = notif_event.get("messageComponents", {}).get(
                    "headline", "N/A"
                )
                created = event.get("creationTime", "N/A")
                lines.append(f"  * [{created}] {event_type}")
                lines.append(f"    {headline[:120]}...")
            if len(sorted_events) > 5:
                lines.append(f"  ... and {len(sorted_events) - 5} more")
    else:
        lines.append("Status: No data")

    # Backup Section
    lines.append("")
    lines.append("BACKUP STATUS")
    if errors_by_check.get("backup"):
        lines.append("Status: ERROR - Backup check failed")
        for prof, err in errors_by_check["backup"][:5]:
            lines.append(f"  * {prof}: {err}")
    else:
        backup_issues = []
        for profile, results in all_results.items():
            backup_data = results.get("backup", {})
            if backup_data.get("failed_jobs", 0) > 0 or backup_data.get("issues"):
                backup_issues.append(profile)

        if not backup_issues:
            lines.append("Status: All backup jobs completed successfully")
        else:
            lines.append(f"Status: {len(backup_issues)} accounts with backup issues")
            for profile in backup_issues:
                backup_data = all_results.get(profile, {}).get("backup", {})
                account_id = get_account_id(profile)
                failed = backup_data.get("failed_jobs", 0)
                total = backup_data.get("total_jobs", 0)
                lines.append(
                    f"  * {profile} ({account_id}): {failed} failed / {total} total jobs"
                )

    # Daily Arbel Section
    lines.append("")
    lines.append("DAILY ARBEL METRICS")
    if errors_by_check.get("daily-arbel"):
        lines.append("Status: ERROR - Daily Arbel check failed")
        for prof, err in errors_by_check["daily-arbel"][:5]:
            lines.append(f"  * {prof}: {err}")
    else:
        rds_warnings = []
        for profile, results in all_results.items():
            rds_data = results.get("daily-arbel", {})
            if rds_data.get("status") == "skipped":
                continue
            instances = rds_data.get("instances", {})
            warn_count = 0
            for data in instances.values():
                for m in data.get("metrics", {}).values():
                    if m.get("status") == "warn":
                        warn_count += 1
            if warn_count > 0:
                rds_warnings.append((profile, warn_count))

        if not rds_warnings:
            lines.append("Status: All RDS metrics normal")
        else:
            lines.append(f"Status: {len(rds_warnings)} accounts with RDS warnings")
            for profile, warn_count in rds_warnings:
                account_id = get_account_id(profile)
                lines.append(
                    f"  * {profile} ({account_id}): {warn_count} metric warnings"
                )

    # Account Coverage
    lines.append("")
    lines.append("-" * 70)
    lines.append("ACCOUNT COVERAGE")
    lines.append("-" * 70)
    lines.append(f"Total Assessed: {len(profiles)} accounts")
    lines.append(f"Clean Accounts: {len(clean_accounts)}")
    lines.append(f"Accounts with Issues: {len(profiles) - len(clean_accounts)}")
    if check_errors:
        lines.append(f"Check Errors: {len(check_errors)} (see below)")

    if check_errors:
        lines.append("")
        lines.append("CHECK ERRORS:")
        for profile, chk, err in check_errors:
            lines.append(f"  - {profile} | {chk}: {err}")

    # Recommendations
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

    if total_anomalies > 0:
        lines.append(f"{rec_count}. COST REVIEW: Investigate cost anomalies")
        affected = [
            p
            for p, r in all_results.items()
            if r.get("cost", {}).get("total_anomalies", 0) > 0
        ]
        lines.append(f"   Affected accounts: {', '.join(affected)}")
        rec_count += 1

    if total_findings > 0:
        lines.append(
            f"{rec_count}. IMMEDIATE ACTION REQUIRED: Investigate GuardDuty findings"
        )
        affected = [
            p
            for p, r in all_results.items()
            if r.get("guardduty", {}).get("findings", 0) > 0
        ]
        lines.append(f"   Affected accounts: {', '.join(affected)}")
        rec_count += 1

    if total_alarms > 0:
        lines.append(f"{rec_count}. INFRASTRUCTURE REVIEW: Address CloudWatch alarms")
        affected = [
            p
            for p, r in all_results.items()
            if r.get("cloudwatch", {}).get("count", 0) > 0
        ]
        lines.append(f"   Affected accounts: {', '.join(affected)}")
        rec_count += 1

    if rec_count == 1:
        lines.append("1. ROUTINE MONITORING: Continue assessment schedule")

    # WhatsApp messages for aryanoble
    if group_name == "Aryanoble":
        date_str_wa = datetime.now(timezone(timedelta(hours=7))).strftime("%d-%m-%Y")

        lines.append("")
        lines.append("=" * 70)
        lines.append("WHATSAPP MESSAGE (READY TO SEND)")
        lines.append("=" * 70)
        lines.append("--backup")
        lines.append(build_whatsapp_backup(date_str_wa, all_results))
        lines.append("")
        lines.append("--rds")
        lines.append(build_whatsapp_rds(all_results))

    lines.append("")
    lines.append("=" * 70)
    lines.append("END OF REPORT")
    lines.append("=" * 70)

    # Print the detailed report
    print("\n" + "\n".join(lines))


def _print_simple_report(
    profiles,
    all_results,
    total_anomalies,
    total_findings,
    total_alarms,
    check_errors,
    guardduty_disabled,
    region,
):
    """Print simplified daily report without backup/RDS sections (aryanoble style)."""

    now = datetime.now()
    date_str = now.strftime("%B %d, %Y")

    lines = []
    lines.append("DAILY MONITORING REPORT")
    lines.append(f"Date: {date_str}")
    lines.append(f"Scope: {len(profiles)} AWS Accounts | Region: {region}")
    lines.append("")
    lines.append("EXECUTIVE SUMMARY")

    summary_bits = []
    if total_findings > 0:
        summary_bits.append(f"{total_findings} new security findings")
    if total_alarms > 0:
        summary_bits.append(f"{total_alarms} infrastructure alerts")
    if total_anomalies > 0:
        summary_bits.append(f"{total_anomalies} cost anomalies")

    if summary_bits:
        summary = "Security assessment completed across "
        summary += f"{len(profiles)} AWS accounts. "
        summary += " and ".join(summary_bits) + " detected requiring attention."
    elif check_errors:
        summary = (
            f"Security assessment completed across {len(profiles)} AWS accounts. "
            f"{len(check_errors)} check error(s) encountered; see CHECK ERRORS."
        )
    else:
        summary = (
            f"Security assessment completed across {len(profiles)} AWS accounts. "
            "No new security incidents detected."
        )

    lines.append(summary)
    lines.append("")
    lines.append("ASSESSMENT RESULTS")
    lines.append("")

    # Cost
    lines.append("COST ANOMALIES")
    if check_errors:
        error_cost = [e for e in check_errors if e[1] == "cost"]
    else:
        error_cost = []
    if error_cost:
        lines.append("Status: ERROR - Cost Anomaly check failed")
    elif total_anomalies == 0:
        lines.append("Status: CLEAR - No cost anomalies detected")
    else:
        lines.append(
            f"Status: ATTENTION REQUIRED - {total_anomalies} anomalies detected"
        )

    lines.append("")

    # GuardDuty
    lines.append("GUARDDUTY FINDINGS")
    gd_errors = [e for e in check_errors if e[1] == "guardduty"]
    if gd_errors:
        lines.append("Status: ERROR - GuardDuty check failed")
    elif total_findings > 0:
        lines.append(
            f"Status: ATTENTION REQUIRED - {total_findings} new findings detected"
        )
        lines.append("")
        lines.append("Current Findings:")
        for profile, results in all_results.items():
            gd_data = results.get("guardduty", {})
            if gd_data.get("findings", 0) > 0:
                account_id = get_account_id(profile)
                lines.append(
                    f"• {profile} ({account_id}): {gd_data['findings']} findings"
                )
                for detail in gd_data.get("details", [])[:3]:
                    lines.append(f"  - Type: {detail.get('type', 'N/A')}")
                    lines.append(f"  - Severity: {detail.get('severity', 'N/A')}")
                    lines.append(f"  - Date: {detail.get('updated', 'N/A')}")
    elif guardduty_disabled:
        lines.append("Status: GuardDuty not enabled on some accounts")
    else:
        lines.append("Status: CLEAR - No new findings detected")

    if guardduty_disabled:
        lines.append("")
        lines.append("GuardDuty NOT ENABLED:")
        for profile in guardduty_disabled:
            account_id = get_account_id(profile)
            lines.append(f"• {profile} ({account_id})")

    lines.append("")

    # CloudWatch
    lines.append("CLOUDWATCH ALARMS")
    cw_errors = [e for e in check_errors if e[1] == "cloudwatch"]
    if cw_errors:
        lines.append("Status: ERROR - CloudWatch check failed")
    elif total_alarms == 0:
        lines.append("Status: All monitoring systems normal")
    else:
        lines.append(f"Status: {total_alarms} alarms in ALARM state")
        lines.append("")
        lines.append("Active Alarms:")
        for profile, results in all_results.items():
            cw_data = results.get("cloudwatch", {})
            if cw_data.get("count", 0) > 0:
                account_id = get_account_id(profile)
                lines.append(
                    f"• {profile} ({account_id}): {cw_data['count']} active alarms"
                )
                for detail in cw_data.get("details", [])[:3]:
                    lines.append(f"  - Alarm: {detail.get('name', 'N/A')}")
                    lines.append(f"  - Reason: {detail.get('reason', 'N/A')}")
                    lines.append(f"  - Date: {detail.get('updated', 'N/A')}")

    lines.append("")

    # Notification Center
    lines.append("NOTIFICATION CENTER")
    notif_errors = [e for e in check_errors if e[1] == "notifications"]
    notif_data = None
    all_notif_events = []
    total_today = 0
    total_managed_all = 0

    for profile, results in all_results.items():
        if "notifications" in results:
            notif_result = results["notifications"]
            if notif_result.get("status") == "success":
                if notif_data is None:
                    notif_data = notif_result
                total_today += notif_result.get("today_count", 0)
                total_managed_all += notif_result.get("total_managed", 0)
                all_notif_events.extend(notif_result.get("all_events", []))

    if notif_errors:
        lines.append("Status: ERROR - Notification Center check failed")
    elif notif_data:
        if total_today == 0:
            lines.append(
                f"Status: No new notifications today ({total_managed_all} existing available)"
            )
        else:
            lines.append(f"Status: {total_today} new notifications detected today")

        # Show all existing notifications from all accounts
        if len(all_notif_events) > 0:
            sorted_events = sorted(
                all_notif_events, key=lambda x: x.get("creationTime", ""), reverse=True
            )
            lines.append("")
            lines.append(f"All Notifications ({len(sorted_events)} total):")
            for event in sorted_events[:5]:
                notif_event = event.get("notificationEvent", {})
                event_type = notif_event.get("sourceEventMetadata", {}).get(
                    "eventType", "N/A"
                )
                headline = notif_event.get("messageComponents", {}).get(
                    "headline", "N/A"
                )
                created = event.get("creationTime", "N/A")
                lines.append(f"  * [{created}] {event_type}")
                lines.append(f"    {headline[:120]}...")
            if len(sorted_events) > 5:
                lines.append(f"  ... and {len(sorted_events) - 5} more")
    else:
        lines.append("Status: No data")

    lines.append("")

    # Account coverage
    lines.append("ACCOUNT COVERAGE")
    lines.append(f"Total Assessed: {len(profiles)} accounts")

    if check_errors:
        lines.append("")
        lines.append("CHECK ERRORS:")
        for profile, chk, err in check_errors:
            lines.append(f"- {profile} | {chk}: {err}")

    print("\n" + "\n".join(lines))
