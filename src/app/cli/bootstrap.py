#!/usr/bin/env python3
"""Canonical CLI bootstrap entrypoint under src/app."""

import argparse
import sys

from src.core.runtime.config import PROFILE_GROUPS, DEFAULT_WORKERS
from src.core.runtime.config_loader import (
    create_sample_config,
    get_config,
    CONFIG_FILE,
    get_sample_config_content,
)
from src.core.runtime.utils import resolve_region
from src.core.runtime.runners import (
    run_individual_check,
    run_all_checks,
    run_group_specific,
)
from src.core.runtime.ui import (
    VERSION,
    console,
    print_success,
    print_info,
    print_error,
    ICONS,
)


def _run_interactive_mode():
    try:
        from src.app.tui.bootstrap import run_interactive

        run_interactive()
    except ModuleNotFoundError as exc:
        if exc.name == "questionary" or "questionary" in str(exc):
            print_error("Install TUI dependencies before using interactive mode.")
            print_info("Try: uv add questionary")
            print_info("Or run non-interactive mode with --check/--all options.")
            sys.exit(2)
        raise


def show_version():
    console.print(
        f"""
[bold cyan]AWS Monitoring Hub[/bold cyan] v{VERSION}

[dim]Centralized AWS Security & Operations Monitoring
https://github.com/alhailrose/monitoring-ics-apps[/dim]
"""
    )


def init_config():
    config = get_config()

    if config.config_exists():
        print_error(f"Config file already exists at {CONFIG_FILE}")
        console.print("[dim]Delete it first if you want to recreate.[/dim]")
        return False

    path = create_sample_config()
    print_success(f"Config file created at {path}")
    console.print()
    console.print("[dim]Sample config content:[/dim]")
    console.print(f"[cyan]{get_sample_config_content()}[/cyan]")
    console.print()
    print_info("Edit this file to add your custom profile groups.")
    return True


def _handle_customer_subcommand(argv):
    """Handle 'monitoring-hub customer <action> [args]' subcommands."""
    from src.app.cli.customer_commands import (
        customer_list,
        customer_scan,
        customer_validate,
    )

    if not argv:
        print_error("Usage: monitoring-hub customer <list|scan|validate> [customer_id]")
        sys.exit(1)

    action = argv[0]

    if action == "list":
        customer_list()
        return

    if action == "scan":
        customer_scan()
        return

    if action == "validate":
        if len(argv) < 2:
            print_error("Usage: monitoring-hub customer validate <customer_id>")
            sys.exit(1)
        success = customer_validate(argv[1])
        sys.exit(0 if success else 1)

    print_error(f"Unknown customer action: {action}")
    print_info("Available: list, scan, validate")
    print_info("")
    print_info("  list     - Show all customer configurations")
    print_info("  scan     - Compare AWS profiles with customer configs")
    print_info("  validate - Validate a customer YAML file")
    print_info("")
    print_info("To add/edit customers, edit YAML files in configs/customers/")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="AWS Monitoring Hub - Centralized AWS monitoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
{ICONS["star"]} Examples:

  # Interactive mode (default)
  monitoring-hub

  # Run individual check
  monitoring-hub --check health --profile ksni-master
  monitoring-hub --check backup --profile ksni-master

  # Run all checks for a group
  monitoring-hub --all --group nabati

  # Run all checks with custom workers
  monitoring-hub --all --group nabati --workers 10

  # Run checks for a customer (with Slack prompt)
  monitoring-hub --customer aryanoble

  # Customer management
  monitoring-hub customer list
  monitoring-hub customer scan
  monitoring-hub customer validate ucoal

  # Initialize config file
  monitoring-hub --init-config

  # Huawei SSO login (external hcloud helper)
  cd /home/heilrose/Work/Monitoring/huawei
  hcloud configure sso --cli-profile=dh_prod_erp-ro
  ./sync_sso_token.sh --source dh_prod_erp-ro
  monitoring-hub --check huawei-ecs-util --profile dh_prod_erp-ro --region ap-southeast-4

  # Note: sync_sso_token.sh is not bundled with monitoring-hub package
  # and must exist on your local machine.

{ICONS["check"]} Available checks: health, cost, guardduty, cloudwatch, notifications, backup, daily-arbel, ec2list, huawei-ecs-util

{ICONS["settings"]} Config file: {CONFIG_FILE}
        """,
    )

    parser.add_argument(
        "--version", "-V", action="store_true", help="Show version information"
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
        help="Create sample config file at ~/.monitoring-hub/config.yaml",
    )
    parser.add_argument(
        "--check",
        help="Run specific check (health, cost, guardduty, cloudwatch, notifications, backup, daily-arbel, ec2list, huawei-ecs-util)",
    )
    parser.add_argument(
        "--all", action="store_true", help="Run all checks (summary mode)"
    )
    parser.add_argument(
        "--include-backup-rds",
        action="store_true",
        help="Include backup and RDS checks in --all mode (default: excluded)",
    )
    parser.add_argument(
        "--interactive", action="store_true", help="Run interactive mode with menu"
    )
    parser.add_argument(
        "--customer",
        help="Run configured checks for a customer (reads configs/customers/<id>.yaml)",
    )
    parser.add_argument("--profile", help="AWS profile name(s), comma-separated")
    parser.add_argument("--aws-profile", help="Alias for --profile")
    parser.add_argument(
        "--group",
        choices=list(PROFILE_GROUPS.keys()),
        help="Profile group (nabati, sadewa, aryanoble, aryanoble-backup, hungryhub, ics, master)",
    )
    parser.add_argument(
        "--sso", choices=list(PROFILE_GROUPS.keys()), help="Alias for --group"
    )
    parser.add_argument(
        "--sso-profile", help="Specific SSO profile name(s), comma-separated"
    )
    parser.add_argument(
        "--region",
        default=None,
        help="AWS region override (defaults to profile config)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Number of parallel workers (default: {DEFAULT_WORKERS})",
    )
    parser.add_argument(
        "--send-slack",
        action="store_true",
        help="Send generated report to configured Slack route",
    )

    # Handle "customer" subcommand before argparse
    if len(sys.argv) >= 2 and sys.argv[1] == "customer":
        _handle_customer_subcommand(sys.argv[2:])
        sys.exit(0)

    args = parser.parse_args()

    if args.version:
        show_version()
        sys.exit(0)

    if args.init_config:
        success = init_config()
        sys.exit(0 if success else 1)

    # Customer mode
    if args.customer:
        from src.core.runtime.customer_runner import run_customer_checks, prompt_and_send_slack

        region = args.region or "ap-southeast-3"
        result = run_customer_checks(
            args.customer, region=region, workers=args.workers
        )
        if result:
            prompt_and_send_slack(result)
        sys.exit(0)

    if args.interactive or (not args.check and not args.all):
        _run_interactive_mode()
        sys.exit(0)

    if args.group and args.sso:
        print_error("Use only one of --group or --sso")
        sys.exit(1)

    aws_profiles_raw = args.profile or args.aws_profile
    sso_profiles_raw = args.sso_profile

    if not any([aws_profiles_raw, sso_profiles_raw, args.group, args.sso]):
        print_error("Must specify --profile, --group, --sso, or --sso-profile")
        sys.exit(1)

    profiles = []
    if aws_profiles_raw:
        profiles.extend([p.strip() for p in aws_profiles_raw.split(",") if p.strip()])
    if sso_profiles_raw:
        profiles.extend([p.strip() for p in sso_profiles_raw.split(",") if p.strip()])

    group_choice = args.group or args.sso
    if group_choice:
        profiles.extend(list(PROFILE_GROUPS[group_choice].keys()))

    seen = set()
    deduped = []
    for p in profiles:
        if p not in seen:
            deduped.append(p)
            seen.add(p)
    profiles = deduped

    if not profiles:
        print_error("No profiles resolved from provided arguments")
        sys.exit(1)

    if args.check == "huawei-ecs-util" and not args.region:
        resolved_region = "ap-southeast-4"
    else:
        resolved_region = resolve_region(profiles, args.region)
    exclude_backup_rds = not args.include_backup_rds

    if args.check:
        if args.check in ["backup", "daily-arbel", "notifications", "huawei-ecs-util"] and len(profiles) > 1:
            run_group_specific(
                args.check,
                profiles,
                resolved_region,
                group_name=group_choice,
                workers=args.workers,
                send_slack=args.send_slack,
            )
        else:
            if len(profiles) > 1:
                print_error("Individual check mode only supports single profile")
                print_info(
                    "Use --all for multiple profiles or use backup/rds/notifications with --group"
                )
                sys.exit(1)
            run_individual_check(
                args.check,
                profiles[0],
                resolved_region,
                send_slack=args.send_slack,
            )
    else:
        run_all_checks(
            profiles,
            resolved_region,
            group_name=group_choice,
            workers=args.workers,
            exclude_backup_rds=exclude_backup_rds,
        )


if __name__ == "__main__":
    main()
