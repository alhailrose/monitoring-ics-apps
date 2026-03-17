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
from src.core.formatting.reports import build_huawei_legacy_consolidated_report
from .ui import (
    console,
    print_check_header,
    print_group_header,
    ICONS,
)
from src.integrations.slack.notifier import send_report_to_slack
from src.checks.common.aws_errors import (
    is_credential_error,
    friendly_credential_message,
)


def run_individual_check(
    check_name: str,
    profile: str,
    region: str,
    send_slack: bool = False,
    check_kwargs: Optional[dict] = None,
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
    checker = checker_class(region=region, **(check_kwargs or {}))

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
            if is_credential_error(exc):
                msg = friendly_credential_message(exc, profile)
                console.print(
                    f"\n[bold red]{ICONS['error']} CREDENTIAL ERROR[/bold red]: {msg}"
                )
            else:
                console.print(
                    f"\n[bold red]{ICONS['error']} ERROR[/bold red]: Failed to run {check_name}: {exc}"
                )
            return
        except Exception as exc:
            if is_credential_error(exc):
                msg = friendly_credential_message(exc, profile)
                console.print(
                    f"\n[bold red]{ICONS['error']} CREDENTIAL ERROR[/bold red]: {msg}"
                )
            else:
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
    checker_class = AVAILABLE_CHECKS.get(check_name)
    if checker_class is None:
        return {"status": "error", "error": f"Unknown check '{check_name}'"}
    checker = checker_class(region=region, **(check_kwargs or {}))

    try:
        results = checker.check(profile, account_id)
    except (BotoCoreError, ClientError) as exc:
        if is_credential_error(exc):
            results = checker._error_result(exc, profile, account_id)
        else:
            results = {"status": "error", "error": str(exc)}
    except Exception as exc:
        if is_credential_error(exc):
            results = checker._error_result(exc, profile, account_id)
        else:
            results = {"status": "error", "error": str(exc)}

    return results


def run_check_headless(
    check_name: str,
    profile: str,
    region: str,
    check_kwargs: Optional[dict] = None,
) -> dict:
    """Run one check without UI printing for API/worker usage."""
    return _check_single_profile(
        check_name=check_name,
        profile=profile,
        region=region,
        check_kwargs=check_kwargs,
    )


def _check_all_for_profile(
    profile: str,
    region: str,
    checks: dict,
    check_kwargs_by_name: Optional[dict] = None,
) -> dict:
    """Run all checks for a single profile. Used for parallel execution."""
    profile_results = {}

    for check_name, checker_class in checks.items():
        check_kwargs = {}
        if check_kwargs_by_name:
            check_kwargs = dict(check_kwargs_by_name.get(check_name, {}) or {})
        checker = checker_class(region=region, **check_kwargs)
        account_id = get_account_id(profile)
        try:
            results = checker.check(profile, account_id)
        except (BotoCoreError, ClientError) as exc:
            if is_credential_error(exc):
                results = checker._error_result(exc, profile, account_id)
            else:
                results = {"status": "error", "error": str(exc)}
        except Exception as exc:
            if is_credential_error(exc):
                results = checker._error_result(exc, profile, account_id)
            else:
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
                    if is_credential_error(exc):
                        results = {
                            "status": "error",
                            "error": friendly_credential_message(exc, profile),
                            "is_credential_error": True,
                        }
                    else:
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
    checks_override: Optional[dict] = None,
    check_kwargs_by_name: Optional[dict] = None,
    output_mode: str = "default",
):
    """Run all checks with parallel execution and detailed text output.

    Args:
        checks_override: Optional dict of {check_name: CheckerClass} to run
            instead of the default ALL_MODE_CHECKS sets. Useful for customer
            reports that only need a subset of checks.
    """

    if checks_override is not None:
        checks = checks_override
    else:
        checks = (
            ALL_MODE_CHECKS_NO_BACKUP_RDS if exclude_backup_rds else ALL_MODE_CHECKS
        )

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
    check_errors = []
    clean_accounts = []
    errors_by_check = {name: [] for name in checks.keys()}

    # Instantiate checkers once for reuse
    checkers = {}
    for name, cls in checks.items():
        check_kwargs = {}
        if check_kwargs_by_name:
            check_kwargs = dict(check_kwargs_by_name.get(name, {}) or {})
        checkers[name] = cls(region=region, **check_kwargs)

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
                    _check_all_for_profile,
                    profile,
                    region,
                    checks,
                    check_kwargs_by_name,
                ): profile
                for profile in profiles
            }

            for future in as_completed(futures):
                profile = futures[future]
                try:
                    profile_results = future.result()
                except Exception as exc:
                    if is_credential_error(exc):
                        err_msg = friendly_credential_message(exc, profile)
                        profile_results = {
                            name: {
                                "status": "error",
                                "error": err_msg,
                                "is_credential_error": True,
                            }
                            for name in checks
                        }
                    else:
                        profile_results = {
                            name: {"status": "error", "error": str(exc)}
                            for name in checks
                        }

                all_results[profile] = profile_results
                progress.update(task, advance=1, current=profile)

                # Track issues generically via checker.count_issues()
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
                    elif chk_name in checkers:
                        issue_count = checkers[chk_name].count_issues(results)
                        if issue_count > 0:
                            has_issue = True

                if not has_issue:
                    clean_accounts.append(profile)

    console.print()

    _print_consolidated_report(
        profiles=profiles,
        all_results=all_results,
        checks=checks,
        checkers=checkers,
        check_errors=check_errors,
        clean_accounts=clean_accounts,
        errors_by_check=errors_by_check,
        region=region,
        group_name=group_name,
        output_mode=output_mode,
    )


def _print_consolidated_report(
    profiles,
    all_results,
    checks,
    checkers,
    check_errors,
    clean_accounts,
    errors_by_check,
    region,
    group_name=None,
    output_mode: str = "default",
):
    """Print consolidated daily monitoring report using checker render_section() methods.

    Replaces the old _print_simple_report and _print_detailed_report with a
    single generic function. Output format is identical.
    """
    now = datetime.now()
    date_str = now.strftime("%B %d, %Y")
    time_str = now.strftime("%H:%M WIB")

    include_backup_rds = "backup" in checks or "daily-arbel" in checks
    is_huawei_only = set(checks.keys()) == {"huawei-ecs-util"}
    scope_label = "Huawei Accounts" if is_huawei_only else "AWS Accounts"

    if output_mode == "huawei_legacy" and is_huawei_only:
        huawei_results = {
            profile: all_results.get(profile, {}).get("huawei-ecs-util", {})
            for profile in profiles
        }
        huawei_errors = [
            (profile, err)
            for profile, chk, err in check_errors
            if chk == "huawei-ecs-util"
        ]
        text = build_huawei_legacy_consolidated_report(
            all_results=huawei_results,
            errors=huawei_errors,
            ordered_profiles=list(profiles),
        )
        print("\n" + text)
        return

    if output_mode == "summary":
        lines = []

        from src.configs.loader import get_profile_metadata

        profile_meta_cache = {}

        def _meta(profile_name: str) -> dict:
            if profile_name not in profile_meta_cache:
                profile_meta_cache[profile_name] = get_profile_metadata(profile_name)
            return profile_meta_cache[profile_name]

        def _profile_label(profile_name: str) -> str:
            meta = _meta(profile_name)
            return f"{meta.get('display_name', profile_name)} ({meta.get('account_id', 'Unknown')})"

        def _fmt_pct(value):
            if isinstance(value, (int, float)):
                return f"{float(value):.2f}%"
            return "N/A"

        hour = now.hour
        if hour < 11:
            greeting = "Selamat Pagi Team"
        elif hour < 15:
            greeting = "Selamat Siang Team"
        elif hour < 18:
            greeting = "Selamat Sore Team"
        else:
            greeting = "Selamat Malam Team"

        lines.append(greeting)
        lines.append("Berikut Alert Monitoring")
        lines.append(now.strftime("%Y.%m.%d"))
        lines.append("")

        util_key = "aws-utilization-3core"
        util_checker = checkers.get(util_key)
        util_issue_total = 0

        if util_checker is not None:
            lines.append("Utilisasi 12 Jam (CPU/MEM/DISK)")
            status_order = {"CRITICAL": 0, "WARNING": 1, "PARTIAL_DATA": 2, "NORMAL": 3}

            for profile in profiles:
                util_result = all_results.get(profile, {}).get(util_key, {})
                profile_label = _profile_label(profile)
                if util_result.get("status") == "error":
                    lines.append(
                        f"- {profile_label}: ERROR - {util_result.get('error', 'unknown error')}"
                    )
                    continue

                util_issue_total += util_checker.count_issues(util_result)
                lines.append(f"- {profile_label}")

                rows = sorted(
                    util_result.get("instances", []) or [],
                    key=lambda row: (
                        status_order.get(str((row or {}).get("status") or "NORMAL"), 9),
                        str((row or {}).get("instance_id") or ""),
                    ),
                )

                thresholds = getattr(util_checker, "thresholds", {}) or {}
                cpu_warn = float(thresholds.get("cpu_warning", 70.0))
                cpu_crit = float(thresholds.get("cpu_critical", 85.0))
                mem_warn = float(thresholds.get("memory_warning", 75.0))
                mem_crit = float(thresholds.get("memory_critical", 90.0))
                disk_warn = float(thresholds.get("disk_free_warning", 20.0))
                disk_crit = float(thresholds.get("disk_free_critical", 10.0))

                grouped = {
                    "CRITICAL": [],
                    "WARNING": [],
                    "PARTIAL_DATA": [],
                    "NORMAL": [],
                }
                for row in rows:
                    status_key = str(row.get("status") or "NORMAL")
                    if status_key in grouped:
                        grouped[status_key].append(row)

                alert_notes = {
                    f"CPU sangat tinggi (>= {cpu_crit:.0f}%)": [],
                    f"CPU tinggi (>= {cpu_warn:.0f}%)": [],
                    f"Memory sangat tinggi (>= {mem_crit:.0f}%)": [],
                    f"Memory tinggi (>= {mem_warn:.0f}%)": [],
                    f"Disk sisa sangat rendah (<= {disk_crit:.0f}%)": [],
                    f"Disk sisa rendah (<= {disk_warn:.0f}%)": [],
                }

                def _add_unique(container, item):
                    if item not in container:
                        container.append(item)

                for status_name in ["CRITICAL", "WARNING", "PARTIAL_DATA", "NORMAL"]:
                    status_rows = grouped.get(status_name) or []
                    for row in status_rows:
                        instance_name = str(row.get("name") or "").strip()
                        if not instance_name or instance_name == "-":
                            instance_name = "instance-tanpa-nama"
                        instance_label = instance_name

                        cpu_peak = row.get("cpu_peak_12h")
                        mem_peak = row.get("memory_peak_12h")
                        disk_free = row.get("disk_free_min_percent")

                        if isinstance(cpu_peak, (int, float)):
                            if float(cpu_peak) >= cpu_crit:
                                _add_unique(
                                    alert_notes[
                                        f"CPU sangat tinggi (>= {cpu_crit:.0f}%)"
                                    ],
                                    instance_label,
                                )
                            elif float(cpu_peak) >= cpu_warn:
                                _add_unique(
                                    alert_notes[f"CPU tinggi (>= {cpu_warn:.0f}%)"],
                                    instance_label,
                                )

                        if isinstance(mem_peak, (int, float)):
                            if float(mem_peak) >= mem_crit:
                                _add_unique(
                                    alert_notes[
                                        f"Memory sangat tinggi (>= {mem_crit:.0f}%)"
                                    ],
                                    instance_label,
                                )
                            elif float(mem_peak) >= mem_warn:
                                _add_unique(
                                    alert_notes[f"Memory tinggi (>= {mem_warn:.0f}%)"],
                                    instance_label,
                                )

                        if isinstance(disk_free, (int, float)):
                            if float(disk_free) <= disk_crit:
                                _add_unique(
                                    alert_notes[
                                        f"Disk sisa sangat rendah (<= {disk_crit:.0f}%)"
                                    ],
                                    instance_label,
                                )
                            elif float(disk_free) <= disk_warn:
                                _add_unique(
                                    alert_notes[
                                        f"Disk sisa rendah (<= {disk_warn:.0f}%)"
                                    ],
                                    instance_label,
                                )

                        metric_parts = []
                        if cpu_peak is not None:
                            metric_parts.append(f"CPU={_fmt_pct(cpu_peak)}")
                        if mem_peak is not None:
                            metric_parts.append(f"MEM={_fmt_pct(mem_peak)}")
                        if disk_free is not None:
                            metric_parts.append(f"DISK={_fmt_pct(disk_free)}")

                        metric_text = (
                            " | ".join(metric_parts)
                            if metric_parts
                            else "metric tidak tersedia"
                        )
                        lines.append(f"    - {instance_name} | {metric_text}")

                if any(alert_notes.values()):
                    lines.append("  *Catatan Alert:*")
                    for key in [
                        f"CPU sangat tinggi (>= {cpu_crit:.0f}%)",
                        f"CPU tinggi (>= {cpu_warn:.0f}%)",
                        f"Memory sangat tinggi (>= {mem_crit:.0f}%)",
                        f"Memory tinggi (>= {mem_warn:.0f}%)",
                        f"Disk sisa sangat rendah (<= {disk_crit:.0f}%)",
                        f"Disk sisa rendah (<= {disk_warn:.0f}%)",
                    ]:
                        items = alert_notes.get(key) or []
                        if not items:
                            continue
                        lines.append(f"    - *{key}: {', '.join(items)}*")
            lines.append("")

        lines.append("Ringkasan Check Lain")
        anomaly_lines = []
        check_status_lines = []
        check_labels = {
            "notifications": "Notifikasi (12 jam)",
            "cost": "Cost Anomaly",
            "guardduty": "GuardDuty Finding",
            "cloudwatch": "Alarm CloudWatch",
        }
        no_issue_messages = {
            "notifications": "tidak ada notifikasi baru",
            "cost": "tidak ada cost anomaly",
            "guardduty": "tidak ada finding",
            "cloudwatch": "tidak ada alarm aktif",
        }
        for chk_name, checker in checkers.items():
            if chk_name == util_key:
                continue
            label = check_labels.get(chk_name, chk_name)
            has_error = False
            total_issues = 0
            error_profiles = []
            for profile in profiles:
                result = all_results.get(profile, {}).get(chk_name, {})
                profile_label = _profile_label(profile)
                if result.get("status") == "error":
                    has_error = True
                    error_profiles.append(profile_label)
                    anomaly_lines.append(
                        f"- {label} - {profile_label}: gagal cek - {result.get('error', 'unknown error')}"
                    )
                    continue

                issue_count = checker.count_issues(result)
                total_issues += int(issue_count or 0)
                if issue_count <= 0:
                    continue

                if chk_name == "cloudwatch":
                    anomaly_lines.append(
                        f"- Alarm CloudWatch - {profile_label}: {result.get('count', issue_count)} alarm aktif"
                    )
                elif chk_name == "notifications":
                    anomaly_lines.append(
                        f"- Notifikasi - {profile_label}: {result.get('recent_count', issue_count)} notifikasi baru (12 jam)"
                    )
                elif chk_name == "guardduty":
                    anomaly_lines.append(
                        f"- GuardDuty Finding - {profile_label}: {issue_count} finding terdeteksi (LOW diabaikan)"
                    )
                elif chk_name == "cost":
                    anomaly_lines.append(
                        f"- Cost Anomaly - {profile_label}: {result.get('total_anomalies', issue_count)} anomaly"
                    )
                else:
                    detail_label = checker.issue_label or "temuan"
                    anomaly_lines.append(
                        f"- {chk_name} - {profile_label}: {issue_count} {detail_label}"
                    )

            if has_error and total_issues == 0:
                check_status_lines.append(
                    f"- {label}: gagal cek pada {', '.join(error_profiles)}"
                )
            elif total_issues == 0:
                check_status_lines.append(
                    f"- {label}: {no_issue_messages.get(chk_name, 'tidak ada temuan')}"
                )
            else:
                check_status_lines.append(f"- {label}: ada temuan")

        lines.extend(check_status_lines)

        if anomaly_lines:
            lines.append("*Temuan Penting*")
            for item in anomaly_lines:
                lines.append(f"*{item}*")
        elif util_issue_total == 0 and not check_errors:
            lines.append("*All Is Ok*")
        else:
            lines.append(
                "*Check lain tidak ada temuan, perhatian ada pada utilisasi di atas.*"
            )

        print("\n" + "\n".join(lines))
        return

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
        lines.append(f"Scope: {len(profiles)} {scope_label} | Region: {region}")
        lines.append("")
        lines.append("-" * 70)
    else:
        lines.append("DAILY MONITORING REPORT")
        lines.append(f"Date: {date_str}")
        lines.append(f"Scope: {len(profiles)} {scope_label} | Region: {region}")
        lines.append("")

    # Executive Summary — generic via checker.count_issues()
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

    if is_huawei_only:
        summary_text = (
            f"Utilization assessment completed across {len(profiles)} Huawei accounts."
        )
    else:
        summary_text = (
            f"Security assessment completed across {len(profiles)} AWS accounts."
        )
    if check_errors:
        summary_text += f" {len(check_errors)} check error(s) encountered; see CHECK ERRORS section."

    if not totals and not check_errors:
        if is_huawei_only:
            summary_text += " No significant utilization findings detected. All systems operating normally."
        else:
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

    # Render each check's section via checker.render_section()
    for chk_name, checker in checkers.items():
        if not checker.supports_consolidated:
            continue
        # Build per-check results dict: {profile: result_for_this_check}
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

    # Recommendations (detailed mode only)
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

    # WhatsApp messages for aryanoble (detailed mode)
    if include_backup_rds and group_name == "Aryanoble":
        date_str_wa = datetime.now(timezone(timedelta(hours=7))).strftime("%d-%m-%Y")

        lines.append("")
        lines.append("=" * 70)
        lines.append("WHATSAPP MESSAGE (READY TO SEND)")
        lines.append("=" * 70)
        lines.append("--backup")
        lines.append(
            build_whatsapp_backup(
                date_str_wa,
                {
                    p: {chk: all_results.get(p, {}).get(chk, {}) for chk in checks}
                    for p in profiles
                },
            )
        )
        lines.append("")
        lines.append("--rds")
        lines.append(
            build_whatsapp_rds(
                {
                    p: {chk: all_results.get(p, {}).get(chk, {}) for chk in checks}
                    for p in profiles
                }
            )
        )

    print("\n" + "\n".join(lines))
