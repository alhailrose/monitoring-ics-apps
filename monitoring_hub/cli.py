#!/usr/bin/env python3
"""
AWS Monitoring Hub CLI
Centralized monitoring for AWS security and operations
"""

import argparse
import sys

from .config import PROFILE_GROUPS, DEFAULT_WORKERS
from .config_loader import (
    create_sample_config,
    get_config,
    CONFIG_FILE,
    get_sample_config_content,
)
from .utils import resolve_region
from .runners import run_individual_check, run_all_checks, run_group_specific
from .interactive import run_interactive
from .ui import VERSION, console, print_success, print_info, print_error, ICONS


def show_version():
    """Display version information."""
    console.print(f"""
[bold cyan]AWS Monitoring Hub[/bold cyan] v{VERSION}

[dim]Centralized AWS Security & Operations Monitoring
https://github.com/alhailrose/monitoring-ics-apps[/dim]
""")


def init_config():
    """Initialize sample configuration file."""
    config = get_config()

    if config.config_exists():
        print_error(f"Config file already exists at {CONFIG_FILE}")
        console.print(f"[dim]Delete it first if you want to recreate.[/dim]")
        return False

    path = create_sample_config()
    print_success(f"Config file created at {path}")
    console.print()
    console.print("[dim]Sample config content:[/dim]")
    console.print(f"[cyan]{get_sample_config_content()}[/cyan]")
    console.print()
    print_info("Edit this file to add your custom profile groups.")
    return True


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
  
  # Initialize config file
  monitoring-hub --init-config

{ICONS["check"]} Available checks: health, cost, guardduty, cloudwatch, notifications, backup, rds, ec2list

{ICONS["settings"]} Config file: {CONFIG_FILE}
        """,
    )

    # Version and config flags
    parser.add_argument(
        "--version", "-V", action="store_true", help="Show version information"
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
        help="Create sample config file at ~/.monitoring-hub/config.yaml",
    )

    # Check flags
    parser.add_argument(
        "--check",
        help="Run specific check (health, cost, guardduty, cloudwatch, notifications, backup, rds, ec2list)",
    )
    parser.add_argument(
        "--all", action="store_true", help="Run all checks (summary mode)"
    )
    parser.add_argument(
        "--no-backup-rds",
        action="store_true",
        help="Skip backup and RDS checks in --all mode (aryanoble style report)",
    )
    parser.add_argument(
        "--interactive", action="store_true", help="Run interactive mode with menu"
    )

    # Profile flags
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

    # Options
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

    args = parser.parse_args()

    # Handle version flag
    if args.version:
        show_version()
        sys.exit(0)

    # Handle init-config flag
    if args.init_config:
        success = init_config()
        sys.exit(0 if success else 1)

    # Default to interactive mode if no check/all flags
    if args.interactive or (not args.check and not args.all):
        run_interactive()
        sys.exit(0)

    # Validate arguments
    if args.group and args.sso:
        print_error("Use only one of --group or --sso")
        sys.exit(1)

    aws_profiles_raw = args.profile or args.aws_profile
    sso_profiles_raw = args.sso_profile

    if not any([aws_profiles_raw, sso_profiles_raw, args.group, args.sso]):
        print_error("Must specify --profile, --group, --sso, or --sso-profile")
        sys.exit(1)

    # Get profiles to check
    profiles = []

    if aws_profiles_raw:
        profiles.extend([p.strip() for p in aws_profiles_raw.split(",") if p.strip()])

    if sso_profiles_raw:
        profiles.extend([p.strip() for p in sso_profiles_raw.split(",") if p.strip()])

    group_choice = args.group or args.sso
    if group_choice:
        profiles.extend(list(PROFILE_GROUPS[group_choice].keys()))

    # Deduplicate while preserving order
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

    resolved_region = resolve_region(profiles, args.region)
    exclude_backup_rds = args.no_backup_rds or group_choice == "aryanoble"

    # Run checks
    if args.check:
        # Special handling: allow backup/rds/notifications across group for WhatsApp-ready output
        if args.check in ["backup", "rds", "notifications"] and len(profiles) > 1:
            run_group_specific(
                args.check,
                profiles,
                resolved_region,
                group_name=group_choice,
                workers=args.workers,
            )
        else:
            if len(profiles) > 1:
                print_error("Individual check mode only supports single profile")
                print_info(
                    "Use --all for multiple profiles or use backup/rds/notifications with --group"
                )
                sys.exit(1)
            run_individual_check(args.check, profiles[0], resolved_region)
    else:
        # All checks mode - summary output
        run_all_checks(
            profiles,
            resolved_region,
            group_name=group_choice,
            workers=args.workers,
            exclude_backup_rds=exclude_backup_rds,
        )


if __name__ == "__main__":
    main()
