"""Customer management CLI subcommands (init, list, validate)."""

from __future__ import annotations

from pathlib import Path

import yaml

from src.configs.loader import list_customers, load_customer_config, _repo_root
from src.configs.schema.validator import validate_customer_config
from src.core.runtime.config import AVAILABLE_CHECKS
from src.core.runtime.ui import console, ICONS


SCAFFOLD_TEMPLATE = {
    "customer_id": "",
    "display_name": "",
    "slack": {
        "webhook_url": "",
        "channel": "",
        "enabled": False,
    },
    "checks": [],
    "accounts": [],
}


def customer_init(customer_id: str) -> bool:
    """Scaffold a new customer config YAML."""
    root = _repo_root()
    customers_dir = root / "configs" / "customers"
    customers_dir.mkdir(parents=True, exist_ok=True)

    target = customers_dir / f"{customer_id}.yaml"
    if target.exists():
        console.print(
            f"[yellow]{ICONS['info']} Customer config already exists: {target}[/yellow]"
        )
        return False

    scaffold = dict(SCAFFOLD_TEMPLATE)
    scaffold["customer_id"] = customer_id
    scaffold["display_name"] = customer_id.replace("-", " ").title()

    with open(target, "w", encoding="utf-8") as f:
        yaml.dump(scaffold, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    console.print(
        f"[green]{ICONS['check']} Customer config created: {target}[/green]"
    )
    console.print("[dim]Edit this file to add accounts, checks, and Slack config.[/dim]")
    return True


def customer_list() -> None:
    """List all configured customers."""
    customers = list_customers()

    if not customers:
        console.print("[yellow]No customer configs found in configs/customers/[/yellow]")
        console.print("[dim]Run: monitoring-hub customer init <customer_id>[/dim]")
        return

    console.print(f"[bold cyan]{ICONS['star']} Configured Customers[/bold cyan]")
    console.print()

    for c in customers:
        slack_status = "[green]Slack ON[/green]" if c.get("slack_enabled") else "[dim]Slack OFF[/dim]"
        checks_str = ", ".join(c.get("checks", [])) or "[dim]none[/dim]"
        error_str = f" [red]({c['error']})[/red]" if c.get("error") else ""

        console.print(
            f"  {c['customer_id']} ({c['display_name']}) "
            f"| {c['account_count']} accounts | {slack_status} | checks: {checks_str}{error_str}"
        )

    console.print()
    console.print(f"[dim]Total: {len(customers)} customer(s)[/dim]")


def customer_validate(customer_id: str) -> bool:
    """Validate a customer config."""
    try:
        cfg = load_customer_config(customer_id)
    except FileNotFoundError:
        console.print(
            f"[red]{ICONS['error']} Customer config not found: {customer_id}[/red]"
        )
        return False
    except Exception as exc:
        console.print(
            f"[red]{ICONS['error']} Failed to load: {exc}[/red]"
        )
        return False

    issues = []

    # Check required fields
    if not cfg.get("customer_id"):
        issues.append("missing customer_id")
    if not cfg.get("accounts"):
        issues.append("no accounts defined")

    # Check checks are valid
    for check_name in cfg.get("checks", []):
        if check_name not in AVAILABLE_CHECKS:
            issues.append(f"unknown check: {check_name}")

    # Check accounts have required fields
    for i, account in enumerate(cfg.get("accounts", [])):
        if not account.get("profile"):
            issues.append(f"account[{i}] missing profile")
        if not account.get("account_id"):
            issues.append(f"account[{i}] missing account_id")

    # Check Slack config
    slack = cfg.get("slack", {})
    if slack.get("enabled") and not slack.get("webhook_url"):
        issues.append("slack.enabled is true but webhook_url is empty")

    if issues:
        console.print(f"[red]{ICONS['error']} Validation failed for {customer_id}:[/red]")
        for issue in issues:
            console.print(f"  - {issue}")
        return False

    display_name = cfg.get("display_name", customer_id)
    account_count = len(cfg.get("accounts", []))
    checks = cfg.get("checks", [])
    slack_ok = "enabled" if slack.get("enabled") and slack.get("webhook_url") else "disabled"

    console.print(f"[green]{ICONS['check']} {customer_id} ({display_name}) is valid[/green]")
    console.print(f"  Accounts: {account_count} | Checks: {', '.join(checks) or 'none'} | Slack: {slack_ok}")
    return True
