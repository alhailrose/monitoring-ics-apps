"""Customer management CLI subcommands (init, list, validate)."""

from __future__ import annotations

from pathlib import Path

import boto3
import yaml

from src.configs.loader import list_customers, load_customer_config, _repo_root
from src.configs.schema.validator import validate_customer_config
from src.core.runtime.config import AVAILABLE_CHECKS
from src.core.runtime.utils import list_local_profiles
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


def classify_profiles_by_mapping(all_profiles: list[str], customers: list[dict]) -> dict[str, list[str]]:
    """Classify profiles as mapped/unmapped based on customer accounts."""
    mapped_profiles = {
        account.get("profile")
        for customer in customers
        for account in (customer.get("accounts") or [])
        if account.get("profile")
    }

    mapped = [profile for profile in all_profiles if profile in mapped_profiles]
    unmapped = [profile for profile in all_profiles if profile not in mapped_profiles]

    return {"mapped": mapped, "unmapped": unmapped}


def sanitize_checks(selected_checks: list[str]) -> list[str]:
    """Normalize and keep only known checks from AVAILABLE_CHECKS."""
    valid_checks = set(AVAILABLE_CHECKS.keys())
    sanitized: list[str] = []
    seen: set[str] = set()

    for check_name in selected_checks:
        if not isinstance(check_name, str):
            continue
        normalized = check_name.strip()
        if normalized in valid_checks and normalized not in seen:
            sanitized.append(normalized)
            seen.add(normalized)

    return sanitized


def upsert_customer_account(
    customer_cfg: dict,
    profile: str,
    account_id: str,
    account_name: str | None = None,
) -> dict:
    """Append or update an account entry by profile in customer config."""
    accounts = list(customer_cfg.get("accounts") or [])

    account_entry = {
        "profile": profile,
        "account_id": str(account_id),
    }
    if account_name:
        account_entry["account_name"] = account_name

    for index, account in enumerate(accounts):
        if account.get("profile") == profile:
            updated = dict(account)
            updated.update(account_entry)
            accounts[index] = updated
            customer_cfg["accounts"] = accounts
            return customer_cfg

    accounts.append(account_entry)
    customer_cfg["accounts"] = accounts
    return customer_cfg


def ensure_profile_assignment_allowed(
    profile: str,
    customers: list[dict],
    target_customer_id: str,
    override: bool = False,
) -> None:
    """Raise when a profile is already assigned to another customer."""
    if override:
        return

    for customer in customers:
        customer_id = customer.get("customer_id")
        if customer_id == target_customer_id:
            continue

        for account in (customer.get("accounts") or []):
            if account.get("profile") == profile:
                raise ValueError(
                    f"Profile '{profile}' is already assigned to customer '{customer_id}'"
                )


def customer_init(customer_id: str) -> bool:
    """Scaffold a new customer config YAML."""
    from src.configs.loader import _user_config_dir
    
    # Use user config directory for persistence
    customers_dir = _user_config_dir()
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


def _customer_yaml_path(customer_id: str) -> Path:
    """Get the path to a customer YAML file, checking multiple locations."""
    from src.configs.loader import _find_existing_path, _user_config_dir
    
    # First try to find existing file
    existing = _find_existing_path(customer_id)
    if existing:
        return existing
    
    # If not found, return user config directory path (where new files will be created)
    return _user_config_dir() / f"{customer_id}.yaml"


def _load_customer_yaml(customer_id: str) -> tuple[Path | None, dict | None]:
    target = _customer_yaml_path(customer_id)
    if not target.exists():
        return None, None
    with open(target, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return target, raw


def _save_customer_yaml(path: Path, cfg: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


def _load_customer_configs_with_errors() -> tuple[list[dict], list[str]]:
    configs = []
    errors = []
    for item in list_customers():
        customer_id = item.get("customer_id")
        if not customer_id:
            continue
        try:
            configs.append(load_customer_config(customer_id))
        except Exception as exc:
            errors.append(f"{customer_id}: {exc}")
    return configs, errors


def _confirm(message: str, default: bool = False) -> bool:
    try:
        import questionary

        ans = questionary.confirm(message, default=default).ask()
        return bool(ans)
    except (ImportError, ModuleNotFoundError):
        default_label = "Y/n" if default else "y/N"
        answer = input(f"{message} [{default_label}] ").strip().lower()
        if not answer:
            return default
        return answer in ("y", "yes")


def _select_many(message: str, choices: list[str], checked: set[str] | None = None) -> list[str] | None:
    checked = checked or set()
    if not choices:
        return []

    try:
        import questionary

        q_choices = [
            questionary.Choice(choice, value=choice, checked=choice in checked)
            for choice in choices
        ]
        return questionary.checkbox(message, choices=q_choices).ask()
    except (ImportError, ModuleNotFoundError):
        console.print(message)
        for i, choice in enumerate(choices, start=1):
            marker = "*" if choice in checked else " "
            console.print(f"  [{i}] {choice} {marker}")
        raw = input("Select by number (comma-separated, blank to cancel): ").strip()
        if not raw:
            return None
        selected = []
        for token in raw.split(","):
            token = token.strip()
            if not token.isdigit():
                continue
            idx = int(token)
            if 1 <= idx <= len(choices):
                value = choices[idx - 1]
                if value not in selected:
                    selected.append(value)
        return selected


def _detect_account_id(profile: str) -> str:
    try:
        session = boto3.Session(profile_name=profile)
        identity = session.client("sts").get_caller_identity()
        account_id = identity.get("Account")
        return str(account_id) if account_id else "Unknown"
    except Exception:
        return "Unknown"


def customer_scan() -> None:
    """Scan local AWS profiles and show mapped/unmapped summary."""
    profiles = sorted(list_local_profiles())
    customers, errors = _load_customer_configs_with_errors()
    classification = classify_profiles_by_mapping(profiles, customers)

    mapped = classification["mapped"]
    unmapped = classification["unmapped"]

    console.print(f"[bold cyan]{ICONS['star']} Customer Profile Scan[/bold cyan]")
    console.print(f"  Local profiles : {len(profiles)}")
    console.print(f"  Mapped         : {len(mapped)}")
    console.print(f"  Unmapped       : {len(unmapped)}")

    if mapped:
        console.print("\n[green]Mapped profiles:[/green]")
        for profile in mapped:
            console.print(f"  - {profile}")

    if errors:
        console.print("\n[yellow]Unreadable customer configs:[/yellow]")
        for err in errors:
            console.print(f"  - {err}")

    if unmapped:
        console.print("\n[yellow]Unmapped profiles:[/yellow]")
        for profile in unmapped:
            console.print(f"  - {profile}")


def customer_assign(customer_id: str) -> bool:
    """Assign one or more local unmapped profiles to a customer config."""
    target_path, target_cfg = _load_customer_yaml(customer_id)
    if target_path is None or target_cfg is None:
        console.print(f"[red]{ICONS['error']} Customer config not found: {customer_id}[/red]")
        return False

    profiles = sorted(list_local_profiles())
    customers, errors = _load_customer_configs_with_errors()
    if errors:
        console.print(
            "[red]Cannot continue assignment while customer configs are unreadable:[/red]"
        )
        for err in errors:
            console.print(f"  - {err}")
        console.print("[dim]Fix invalid customer config(s) and retry.[/dim]")
        return False

    classification = classify_profiles_by_mapping(profiles, customers)
    unmapped = classification["unmapped"]

    if not unmapped:
        console.print("[yellow]No unmapped local AWS profiles found.[/yellow]")
        return True

    selected = _select_many(
        f"Select profile(s) to assign to '{customer_id}'",
        unmapped,
    )
    if selected is None:
        console.print("[dim]Assignment canceled.[/dim]")
        return False
    if not selected:
        console.print("[yellow]No profiles selected.[/yellow]")
        return False

    changed = False
    assigned = 0
    skipped = 0

    for profile in selected:
        allow = True
        try:
            ensure_profile_assignment_allowed(
                profile=profile,
                customers=customers,
                target_customer_id=customer_id,
                override=False,
            )
        except ValueError as exc:
            allow = _confirm(f"{exc}. Override and continue?", default=False)

        if not allow:
            skipped += 1
            continue

        account_id = _detect_account_id(profile)
        if account_id == "Unknown":
            proceed = _confirm(
                f"Could not detect account ID for '{profile}'. Save with account_id='Unknown'?",
                default=False,
            )
            if not proceed:
                console.print(f"[yellow]Skipped '{profile}' (unknown account_id).[/yellow]")
                skipped += 1
                continue

        upsert_customer_account(target_cfg, profile=profile, account_id=account_id)
        assigned += 1
        changed = True

    if not changed:
        console.print("[yellow]No changes were applied.[/yellow]")
        return False

    _save_customer_yaml(target_path, target_cfg)
    console.print(
        f"[green]{ICONS['check']} Updated {customer_id}: assigned {assigned} profile(s)[/green]"
    )
    if skipped:
        console.print(f"[dim]Skipped {skipped} profile(s).[/dim]")
    return True


def customer_checks(customer_id: str) -> bool:
    """Interactively update checks list for a customer config."""
    target_path, target_cfg = _load_customer_yaml(customer_id)
    if target_path is None or target_cfg is None:
        console.print(f"[red]{ICONS['error']} Customer config not found: {customer_id}[/red]")
        return False

    check_names = sorted(AVAILABLE_CHECKS.keys())
    existing_checks = set(target_cfg.get("checks") or [])
    selected = _select_many(
        f"Select checks for '{customer_id}'",
        check_names,
        checked=existing_checks,
    )
    if selected is None:
        console.print("[dim]Checks update canceled.[/dim]")
        return False

    target_cfg["checks"] = sanitize_checks(selected)
    _save_customer_yaml(target_path, target_cfg)
    checks_str = ", ".join(target_cfg["checks"]) or "none"
    console.print(
        f"[green]{ICONS['check']} Updated checks for {customer_id}: {checks_str}[/green]"
    )
    return True


def customer_sync_accounts(customer_id: str) -> bool:
    """Fetch and update Account IDs for all profiles in a customer config."""
    target_path, target_cfg = _load_customer_yaml(customer_id)
    if target_path is None or target_cfg is None:
        console.print(f"[red]{ICONS['error']} Customer config not found: {customer_id}[/red]")
        return False

    accounts = target_cfg.get("accounts", [])
    if not accounts:
        console.print(f"[yellow]No accounts found for customer '{customer_id}'[/yellow]")
        return False

    console.print(f"[cyan]{ICONS['star']} Syncing Account IDs for {customer_id}...[/cyan]")
    console.print()

    updated = 0
    failed = 0
    unchanged = 0

    for account in accounts:
        profile = account.get("profile")
        current_id = account.get("account_id", "")
        
        if not profile:
            console.print(f"  [yellow]⚠ Skipped: No profile name[/yellow]")
            failed += 1
            continue

        console.print(f"  [dim]Fetching Account ID for profile '{profile}'...[/dim]", end=" ")
        
        detected_id = _detect_account_id(profile)
        
        if detected_id == "Unknown":
            console.print(f"[red]Failed[/red]")
            failed += 1
            continue
        
        if current_id == detected_id:
            console.print(f"[dim]Unchanged ({detected_id})[/dim]")
            unchanged += 1
            continue
        
        account["account_id"] = detected_id
        console.print(f"[green]✓ {detected_id}[/green]")
        updated += 1

    if updated > 0:
        _save_customer_yaml(target_path, target_cfg)
        console.print()
        console.print(
            f"[green]{ICONS['check']} Updated {updated} account(s) for {customer_id}[/green]"
        )
    
    if unchanged > 0:
        console.print(f"[dim]  {unchanged} account(s) unchanged[/dim]")
    
    if failed > 0:
        console.print(f"[yellow]  {failed} account(s) failed to fetch[/yellow]")

    return updated > 0
