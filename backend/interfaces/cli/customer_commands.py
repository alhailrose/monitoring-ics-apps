"""Customer management CLI subcommands (list, scan, validate)."""

from __future__ import annotations

from pathlib import Path

import yaml

from backend.config.loader import list_customers, load_customer_config
from backend.config.schema.validator import validate_customer_config
from backend.domain.runtime.utils import list_local_profiles
from backend.domain.runtime.ui import (
    console,
    ICONS,
    print_error,
    print_info,
    print_success,
)


def classify_profiles_by_mapping(
    all_profiles: list[str], customers: list[dict]
) -> dict[str, list[str]]:
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


def _load_customer_configs_with_errors() -> tuple[list[dict], list[str]]:
    """Load all customer configs, returning valid configs and error messages."""
    customers = []
    errors = []

    for customer_info in list_customers():
        customer_id = customer_info["customer_id"]
        try:
            cfg = load_customer_config(customer_id)
            if cfg:
                customers.append(cfg)
        except Exception as e:
            errors.append(f"{customer_id}: {str(e)}")

    return customers, errors


def customer_list() -> None:
    """List all customer configurations found in the system."""
    console.print(f"[bold cyan]{ICONS['star']} Customer Configurations[/bold cyan]\n")

    customers = list(list_customers())
    if not customers:
        console.print("[yellow]No customer configurations found.[/yellow]")
        console.print("[dim]Create YAML files in configs/customers/ directory.[/dim]")
        return

    for customer_info in customers:
        customer_id = customer_info["customer_id"]
        display_name = customer_info.get("display_name", customer_id)
        account_count = customer_info.get("account_count", 0)
        checks = customer_info.get("checks", [])
        config_path = customer_info.get("path", "unknown")
        slack_enabled = customer_info.get("slack_enabled", False)

        console.print(f"[green]●[/green] {customer_id}")
        console.print(f"  Name: {display_name}")
        console.print(f"  Accounts: {account_count}")
        console.print(f"  Checks: {', '.join(checks) if checks else 'none'}")
        console.print(f"  Slack: {'enabled' if slack_enabled else 'disabled'}")
        console.print(f"  Path: [dim]{config_path}[/dim]")
        console.print()


def customer_scan() -> None:
    """Compare local AWS profiles with customer configs - show mapped/unmapped."""
    profiles = sorted(list_local_profiles())
    customers, errors = _load_customer_configs_with_errors()
    classification = classify_profiles_by_mapping(profiles, customers)

    mapped = classification["mapped"]
    unmapped = classification["unmapped"]

    console.print(f"[bold cyan]{ICONS['star']} Customer Profile Scan[/bold cyan]")
    console.print()
    console.print(f"  Total AWS profiles : {len(profiles)}")
    console.print(f"  Mapped to customers: {len(mapped)}")
    console.print(f"  Unmapped           : {len(unmapped)}")

    if errors:
        console.print()
        console.print("[yellow]⚠ Unreadable customer configs:[/yellow]")
        for err in errors:
            console.print(f"  - {err}")

    if mapped:
        console.print()
        console.print("[green]✓ Mapped profiles:[/green]")
        # Group by customer for better readability
        profile_to_customer = {}
        for customer in customers:
            customer_id = customer.get("customer_id", "unknown")
            for account in customer.get("accounts", []):
                profile = account.get("profile")
                if profile:
                    profile_to_customer[profile] = customer_id

        for profile in sorted(mapped):
            customer_id = profile_to_customer.get(profile, "unknown")
            console.print(f"  - {profile} [dim]→ {customer_id}[/dim]")

    if unmapped:
        console.print()
        console.print("[yellow]⚠ Unmapped profiles:[/yellow]")
        console.print("[dim]  (These profiles are not assigned to any customer)[/dim]")
        for profile in sorted(unmapped):
            console.print(f"  - {profile}")
        console.print()
        console.print(
            "[dim]To map a profile, edit configs/customers/<customer>.yaml[/dim]"
        )


def customer_validate(customer_id: str) -> bool:
    """Validate a customer configuration file."""
    try:
        cfg = load_customer_config(customer_id)
        if not cfg:
            console.print(
                f"[red]{ICONS['error']} Customer config not found: {customer_id}[/red]"
            )
            return False

        # Validate using schema - raises ValueError on error
        try:
            validate_customer_config(cfg)
        except ValueError as e:
            console.print(
                f"[red]{ICONS['error']} Validation failed for {customer_id}:[/red]"
            )
            console.print(f"  {str(e)}")
            return False

        console.print(f"[green]{ICONS['check']} Valid: {customer_id}[/green]")

        # Show summary
        display_name = cfg.get("display_name", customer_id)
        accounts = cfg.get("accounts", [])
        checks = cfg.get("checks", [])

        console.print(f"  Name: {display_name}")
        console.print(f"  Accounts: {len(accounts)}")
        if accounts:
            for account in accounts:
                profile = account.get("profile", "?")
                display = account.get("display_name", profile)
                console.print(f"    - {profile} [dim]({display})[/dim]")
        console.print(f"  Checks: {', '.join(checks) if checks else 'none'}")

        return True

    except Exception as e:
        console.print(f"[red]{ICONS['error']} Error validating {customer_id}:[/red]")
        console.print(f"  {str(e)}")
        return False


def customer_init(customer_id: str) -> bool:
    """Initialize a minimal customer YAML config file."""
    if not customer_id.strip():
        print_error("customer_id is required")
        return False

    target_path = Path("configs/customers") / f"{customer_id}.yaml"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists():
        print_error(f"Customer config already exists: {target_path}")
        return False

    payload = {
        "customer_id": customer_id,
        "display_name": customer_id,
        "check_mode": "summary",
        "checks": ["health", "guardduty", "cloudwatch", "notifications"],
        "accounts": [],
        "slack": {"enabled": False},
    }

    with target_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)

    print_success(f"Created customer config: {target_path}")
    print_info("Edit the accounts list to add AWS profiles.")
    return True


def customer_assign(customer_id: str) -> bool:
    """Assign profiles to a customer via YAML workflow guidance."""
    try:
        load_customer_config(customer_id)
    except Exception as exc:
        print_error(f"Customer config not found or invalid: {exc}")
        return False

    print_info(
        f"Use configs/customers/{customer_id}.yaml to assign profiles under 'accounts'."
    )
    return True


def customer_checks(customer_id: str) -> bool:
    """Show guidance for configuring check list in customer YAML."""
    try:
        cfg = load_customer_config(customer_id)
    except Exception as exc:
        print_error(f"Customer config not found or invalid: {exc}")
        return False

    checks = cfg.get("checks", []) if isinstance(cfg, dict) else []
    print_info(
        f"Current checks for {customer_id}: {', '.join(checks) if checks else '-'}"
    )
    print_info(f"Update configs/customers/{customer_id}.yaml field 'checks' as needed.")
    return True
