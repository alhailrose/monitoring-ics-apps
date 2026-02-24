"""Customer-centric check runner.

Loads a customer config, runs the configured checks across all accounts,
displays results, and optionally sends to the customer's Slack channel.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)

from src.checks.common.aws_errors import is_credential_error, friendly_credential_message
from src.configs.loader import load_customer_config
from src.core.runtime.config import AVAILABLE_CHECKS, DEFAULT_WORKERS
from src.core.runtime.ui import console, ICONS
from src.core.runtime.utils import get_account_id
from src.integrations.slack.notifier import send_to_webhook

logger = logging.getLogger(__name__)


def _run_check_for_account(
    check_name: str, profile: str, account_id: str, region: str, check_kwargs: Optional[dict] = None
) -> dict:
    """Run a single check on a single account."""
    if check_name not in AVAILABLE_CHECKS:
        return {"status": "error", "error": f"Unknown check: {check_name}"}

    checker_class = AVAILABLE_CHECKS[check_name]
    checker = checker_class(region=region, **(check_kwargs or {}))

    try:
        return checker.check(profile, account_id)
    except Exception as exc:
        if is_credential_error(exc):
            return checker._error_result(exc, profile, account_id)
        return {"status": "error", "error": str(exc)}


def run_customer_checks(
    customer_id: str,
    region: str = "ap-southeast-3",
    workers: int = DEFAULT_WORKERS,
) -> Optional[dict]:
    """Run all configured checks for a customer.

    Returns dict with customer info and all results, or None on config error.
    """
    try:
        cfg = load_customer_config(customer_id)
    except FileNotFoundError:
        console.print(
            f"[bold red]{ICONS['error']} ERROR[/bold red]: Customer config not found: {customer_id}"
        )
        console.print("[dim]Run: monitoring-hub customer init {0}[/dim]".format(customer_id))
        return None
    except Exception as exc:
        console.print(
            f"[bold red]{ICONS['error']} ERROR[/bold red]: Failed to load customer config: {exc}"
        )
        return None

    display_name = cfg.get("display_name", customer_id)
    checks = cfg.get("checks", [])
    accounts = cfg.get("accounts", [])

    if not checks:
        console.print(
            f"[yellow]{ICONS['info']} No checks configured for customer {display_name}[/yellow]"
        )
        return None

    if not accounts:
        console.print(
            f"[yellow]{ICONS['info']} No accounts configured for customer {display_name}[/yellow]"
        )
        return None

    # Header
    console.print()
    console.print(
        f"[bold cyan]{ICONS['star']} Customer: {display_name}[/bold cyan]"
    )
    console.print(
        f"[dim]Checks: {', '.join(checks)} | Accounts: {len(accounts)} | Region: {region}[/dim]"
    )
    console.print()

    # Build work items: (check_name, profile, account_id, display_name)
    work_items = []
    for check_name in checks:
        if check_name not in AVAILABLE_CHECKS:
            console.print(
                f"[yellow]{ICONS['info']} Skipping unknown check: {check_name}[/yellow]"
            )
            continue
        for account in accounts:
            profile = account.get("profile")
            acct_id = account.get("account_id", get_account_id(profile) if profile else "Unknown")
            work_items.append((check_name, profile, str(acct_id)))

    if not work_items:
        console.print("[yellow]No valid check/account combinations to run.[/yellow]")
        return None

    # Run checks in parallel
    all_results = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}[/bold cyan]"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        TextColumn("[dim]{task.fields[current]}[/dim]"),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"Running {len(work_items)} checks...",
            total=len(work_items),
            current="",
        )

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {}
            for check_name, profile, acct_id in work_items:
                future = executor.submit(
                    _run_check_for_account, check_name, profile, acct_id, region
                )
                futures[future] = (check_name, profile, acct_id)

            for future in as_completed(futures):
                check_name, profile, acct_id = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    if is_credential_error(exc):
                        result = {
                            "status": "error",
                            "error": friendly_credential_message(exc, profile),
                            "is_credential_error": True,
                        }
                    else:
                        result = {"status": "error", "error": str(exc)}

                if profile not in all_results:
                    all_results[profile] = {}
                all_results[profile][check_name] = result
                progress.update(task, advance=1, current=f"{profile}/{check_name}")

    console.print()

    # Display results per account per check
    for account in accounts:
        profile = account.get("profile")
        acct_display = account.get("display_name", profile)
        acct_id = account.get("account_id", "")
        profile_results = all_results.get(profile, {})

        console.print(f"[bold]== {acct_display} ({acct_id}) ==[/bold]")

        for check_name in checks:
            if check_name not in AVAILABLE_CHECKS:
                continue
            result = profile_results.get(check_name)
            if not result:
                console.print(f"  [{check_name}] No result")
                continue

            checker_class = AVAILABLE_CHECKS[check_name]
            checker = checker_class(region=region)
            report = checker.format_report(result)
            print(report)
            print()

    return {
        "customer_id": customer_id,
        "display_name": display_name,
        "config": cfg,
        "results": all_results,
    }


def prompt_and_send_slack(customer_result: dict) -> bool:
    """Prompt operator to send results to customer's Slack channel.

    Returns True if sent successfully.
    """
    cfg = customer_result.get("config", {})
    display_name = customer_result.get("display_name", "")
    slack_cfg = cfg.get("slack", {})

    if not slack_cfg.get("enabled"):
        console.print(
            f"[dim]Slack not enabled for {display_name}. "
            f"Add slack.enabled: true to customer config.[/dim]"
        )
        return False

    webhook_url = slack_cfg.get("webhook_url", "")
    channel = slack_cfg.get("channel", "")

    if not webhook_url:
        console.print(
            f"[yellow]{ICONS['info']} Slack webhook_url not configured for {display_name}[/yellow]"
        )
        return False

    channel_display = channel or "(default channel)"

    try:
        import questionary
        send = questionary.confirm(
            f"Kirim report ke Slack {display_name} ({channel_display})?",
            default=False,
        ).ask()
    except (ImportError, ModuleNotFoundError):
        # Fallback to simple input if questionary not available
        answer = input(
            f"Kirim report ke Slack {display_name} ({channel_display})? [y/N] "
        ).strip().lower()
        send = answer in ("y", "yes")

    if not send:
        console.print("[dim]Slack send skipped.[/dim]")
        return False

    # Build aggregated report text
    report_lines = [f"Monitoring Report: {display_name}", ""]
    results = customer_result.get("results", {})
    checks = cfg.get("checks", [])
    accounts = cfg.get("accounts", [])

    for account in accounts:
        profile = account.get("profile")
        acct_display = account.get("display_name", profile)
        acct_id = account.get("account_id", "")
        profile_results = results.get(profile, {})

        report_lines.append(f"== {acct_display} ({acct_id}) ==")

        for check_name in checks:
            if check_name not in AVAILABLE_CHECKS:
                continue
            result = profile_results.get(check_name)
            if not result:
                continue

            checker_class = AVAILABLE_CHECKS[check_name]
            checker = checker_class(region="ap-southeast-3")
            report = checker.format_report(result)
            report_lines.append(report)
            report_lines.append("")

    full_report = "\n".join(report_lines)

    sent, reason = send_to_webhook(webhook_url, full_report, channel=channel or None)
    if sent:
        console.print(
            f"[green]{ICONS['check']} Report sent to Slack {display_name} ({channel_display})[/green]"
        )
    else:
        console.print(
            f"[red]{ICONS['error']} Failed to send to Slack: {reason}[/red]"
        )

    return sent
