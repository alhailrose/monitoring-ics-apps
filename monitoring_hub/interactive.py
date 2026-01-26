"""
Interactive menu system for AWS Monitoring Hub.
Beautiful UI with icons, progress bars, and better formatting.
"""

import sys
from datetime import datetime, timedelta
from time import monotonic

import boto3
import questionary
from botocore.exceptions import BotoCoreError, ClientError
from rich.panel import Panel
from rich.table import Table
from rich import box

from checks import cloudwatch_cost_report as cw_cost_report

from .config import (
    PROFILE_GROUPS,
    AVAILABLE_CHECKS,
    INTERRUPT_EXIT_WINDOW,
    CUSTOM_STYLE,
    get_last_interrupt_ts,
    set_last_interrupt_ts,
)
from .config_loader import get_config, create_sample_config, CONFIG_FILE
from .utils import resolve_region, get_account_id, list_local_profiles
from .runners import run_individual_check, run_group_specific, run_all_checks
from .ui import (
    console,
    print_banner,
    print_mini_banner,
    print_tips,
    print_success,
    print_error,
    print_warning,
    print_info,
    print_section_header,
    ICONS,
    VERSION,
)


def _handle_interrupt(context="Kembali ke menu utama", exit_direct=False):
    """Handle Ctrl+C/Esc; in menus we exit immediately for convenience."""
    now = monotonic()
    if exit_direct:
        console.print(
            f"\n[bold green]{ICONS['exit']} Keluar dari AWS Monitoring Hub. Sampai jumpa![/bold green]\n"
        )
        sys.exit(0)
    last_ts = get_last_interrupt_ts()
    if now - last_ts <= INTERRUPT_EXIT_WINDOW:
        console.print(
            f"\n[bold green]{ICONS['exit']} Keluar dari AWS Monitoring Hub. Sampai jumpa![/bold green]\n"
        )
        sys.exit(0)
    set_last_interrupt_ts(now)
    console.print(
        f"\n[bold yellow]{ICONS['warning']} {context}[/bold yellow]. Tekan Ctrl+C lagi untuk keluar.\n"
    )


def _select_prompt(prompt, choices, default=None):
    """Beautiful select prompt with icons."""
    try:
        ans = questionary.select(
            prompt,
            choices=choices,
            default=default
            if default in [c if isinstance(c, str) else c.value for c in choices]
            else None,
            style=CUSTOM_STYLE,
            instruction="(Gunakan ↑↓ untuk navigasi, Enter untuk pilih)",
        ).ask()
    except KeyboardInterrupt:
        _handle_interrupt(exit_direct=True)
        return None
    return ans or None


def _checkbox_prompt(prompt, choices):
    """Beautiful checkbox prompt."""
    try:
        ans = questionary.checkbox(
            prompt,
            choices=choices,
            style=CUSTOM_STYLE,
            instruction="(Spasi untuk pilih, Enter untuk konfirmasi)",
        ).ask()
    except KeyboardInterrupt:
        _handle_interrupt(exit_direct=True)
        return None
    return ans or None


def _choose_region(selected_profiles):
    """Region selection with beautiful UI."""
    default_region = resolve_region(selected_profiles, None)
    region_choices = [
        questionary.Choice(f"🌏 Jakarta (ap-southeast-3)", value="ap-southeast-3"),
        questionary.Choice(f"🌏 Singapore (ap-southeast-1)", value="ap-southeast-1"),
        questionary.Choice(f"🌎 N. Virginia (us-east-1)", value="us-east-1"),
        questionary.Choice(f"🌎 Oregon (us-west-2)", value="us-west-2"),
        questionary.Choice(f"⌨️  Custom region...", value="other"),
    ]

    region = _select_prompt(f"{ICONS['settings']} Pilih Region", region_choices)
    if region is None:
        return None
    if region == "other":
        try:
            region = questionary.text(
                "Masukkan region (contoh: eu-west-1):",
                style=CUSTOM_STYLE,
            ).ask()
        except KeyboardInterrupt:
            _handle_interrupt(exit_direct=True)
            return None
    return region


def _pick_profiles(allow_multiple=True):
    """Profile picker with beautiful UI."""
    source_choices = [
        questionary.Choice(
            f"{ICONS['settings']} Group (SSO) - Profil terdaftar", value="group"
        ),
        questionary.Choice(
            f"{ICONS['ec2list']} Local Profiles - AWS CLI config", value="local"
        ),
    ]

    source = _select_prompt(f"{ICONS['settings']} Sumber Profil", source_choices)
    if not source:
        return [], None, True

    profiles = []
    group_choice = None

    if source == "group":
        # Group selection with profile counts
        group_choices = [
            questionary.Choice(
                f"{ICONS['dot']} {name} ({len(profs)} profiles)", value=name
            )
            for name, profs in PROFILE_GROUPS.items()
        ]

        group_choice = _select_prompt(f"{ICONS['all']} Pilih Group", group_choices)
        if not group_choice:
            return [], None, True

        choices = list(PROFILE_GROUPS[group_choice].keys())
        if allow_multiple:
            # Add select all option
            profiles = _checkbox_prompt(
                f"{ICONS['check']} Pilih Akun dari {group_choice}", choices
            )
        else:
            selected = _select_prompt(f"{ICONS['single']} Pilih Akun", choices)
            profiles = [selected] if selected else []
    else:
        local_profiles = list_local_profiles()
        if not local_profiles:
            print_error(
                "Tidak menemukan profil AWS lokal. Silakan configure AWS CLI terlebih dulu."
            )
            return [], None, False

        if allow_multiple:
            profiles = _checkbox_prompt(
                f"{ICONS['check']} Pilih Profil Lokal", local_profiles
            )
        else:
            selected = _select_prompt(f"{ICONS['single']} Pilih Profil", local_profiles)
            profiles = [selected] if selected else []

    return profiles or [], group_choice, False


def _pause():
    """Pause and wait for user input."""
    console.print()
    try:
        questionary.press_any_key_to_continue(
            message="Tekan Enter untuk kembali ke menu utama...",
            style=CUSTOM_STYLE,
        ).ask()
    except (KeyboardInterrupt, AttributeError):
        # press_any_key_to_continue might not be available in older versions
        try:
            questionary.text(
                "Tekan Enter untuk kembali...",
                style=CUSTOM_STYLE,
                default="",
            ).ask()
        except KeyboardInterrupt:
            _handle_interrupt(exit_direct=True)


def _format_cw_plain(rows, names, start, end, region, top):
    """Teams-friendly plain text for CloudWatch cost report."""
    rows_sorted = sorted(rows, key=lambda r: r["cost"], reverse=True)
    if top > 0:
        rows_sorted = rows_sorted[:top]

    lines = []
    lines.append(f"CloudWatch Cost & Usage ({region})")
    lines.append(
        f"Periode: {start} s/d {(datetime.fromisoformat(end) - timedelta(days=1)).date()}"
    )
    lines.append("")
    lines.append(
        f"{'#':>2}  {'Account':<12} {'Name':<38} {'Cost USD':>9} {'UsageQty':>12}"
    )
    lines.append("-" * 80)

    total_cost = sum(r["cost"] for r in rows)
    total_usage = sum(r["usage"] for r in rows)

    for idx, r in enumerate(rows_sorted, start=1):
        acct = r["account"]
        name = (names.get(acct, "") or "")[:38]
        cost = float(r["cost"])
        usage = float(r["usage"])
        lines.append(f"{idx:>2}  {acct:<12} {name:<38} {cost:>9.2f} {usage:>12,.2f}")

    lines.append("-" * 80)
    lines.append(
        f"{'':>2}  {'':<12} {'TOTAL':<38} {float(total_cost):>9.2f} {float(total_usage):>12,.2f}"
    )
    return "\n".join(lines)


def run_cloudwatch_cost_report():
    """Interactive CloudWatch cost & usage report."""
    print_mini_banner()
    print_section_header("CloudWatch Cost Report", ICONS["cost"])

    profile = "ksni-master"
    region = _choose_region([]) or "ap-southeast-3"

    format_choices = [
        questionary.Choice(f"{ICONS['dot']} Teams (plain text)", value="teams"),
        questionary.Choice(f"{ICONS['dot']} Markdown table", value="markdown"),
        questionary.Choice(f"{ICONS['dot']} Rich table (terminal)", value="table"),
    ]

    fmt_choice = _select_prompt(f"{ICONS['settings']} Format Output", format_choices)
    if not fmt_choice:
        return

    # Top N
    try:
        top_str = questionary.text(
            "Top berapa akun?",
            default="10",
            style=CUSTOM_STYLE,
        ).ask()
    except KeyboardInterrupt:
        _handle_interrupt(exit_direct=True)
        return

    try:
        top_n = int(top_str) if top_str else 10
    except ValueError:
        top_n = 10

    # Date range defaults to MTD
    start = datetime.now().date().replace(day=1)
    end = datetime.now().date() + timedelta(days=1)

    print_info(f"Mengambil data cost untuk region {region}...")

    try:
        session = boto3.Session(profile_name=profile)
        names = cw_cost_report.fetch_account_names(session)
        rows = cw_cost_report.fetch_cost_usage(
            session, (start.isoformat(), end.isoformat()), region
        )
    except (BotoCoreError, ClientError) as exc:
        print_error(f"Gagal mengambil data Cost Explorer: {exc}")
        return
    except Exception as exc:
        print_error(f"Error tak terduga: {exc}")
        return

    console.print()

    if fmt_choice == "table":
        table = cw_cost_report.format_table(
            rows, names, start.isoformat(), end.isoformat(), region, top_n
        )
        console.print(table)
    elif fmt_choice == "markdown":
        md = cw_cost_report.format_markdown(
            rows, names, start.isoformat(), end.isoformat(), region, top_n
        )
        console.print(md)
    else:  # Teams plain text
        text = _format_cw_plain(
            rows, names, start.isoformat(), end.isoformat(), region, top_n
        )
        console.print(
            Panel(text, title="[bold]Cost Report[/bold]", border_style="cyan")
        )


def run_arbel_check():
    """Run Arbel-specific checks (Backup + RDS for aryanoble accounts)."""
    print_mini_banner()
    print_section_header("Arbel Check", ICONS["arbel"])

    arbel_choices = [
        questionary.Choice(
            f"{ICONS['backup']} Backup - Semua akun AryaNoble", value="backup"
        ),
        questionary.Choice(
            f"{ICONS['rds']} RDS Metrics - connect-prod & cis-erha", value="rds"
        ),
    ]

    choice = _select_prompt(f"{ICONS['arbel']} Pilih Check", arbel_choices)
    if not choice:
        return

    region = "ap-southeast-3"

    if choice == "backup":
        profiles = list(PROFILE_GROUPS["aryanoble-backup"].keys())
        run_group_specific("backup", profiles, region, group_name="aryanoble-backup")
    elif choice == "rds":
        profiles = ["connect-prod", "cis-erha"]
        run_group_specific("rds", profiles, region, group_name="aryanoble-backup")


def run_settings_menu():
    """Settings and configuration menu."""
    print_mini_banner()
    print_section_header("Settings & Info", ICONS["settings"])

    config = get_config()

    # Show config info
    info_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    info_table.add_column("Key", style="dim")
    info_table.add_column("Value")

    info_table.add_row("Version", VERSION)
    info_table.add_row("Config File", str(CONFIG_FILE))
    info_table.add_row(
        "Config Exists",
        "[green]Yes[/green]"
        if config.config_exists()
        else "[dim]No (using defaults)[/dim]",
    )
    info_table.add_row("Default Region", config.default_region)
    info_table.add_row("Parallel Workers", str(config.default_workers))
    info_table.add_row("Profile Groups", str(len(list(PROFILE_GROUPS.keys()))))

    console.print(info_table)
    console.print()

    settings_choices = [
        questionary.Choice(
            f"{ICONS['settings']} Create sample config", value="create_config"
        ),
        questionary.Choice(f"{ICONS['info']} Show config path", value="show_path"),
        questionary.Choice(f"{ICONS['arrow']} Back to main menu", value="back"),
    ]

    choice = _select_prompt(f"{ICONS['settings']} Settings", settings_choices)

    if choice == "create_config":
        if config.config_exists():
            print_warning(f"Config sudah ada di {CONFIG_FILE}")
        else:
            path = create_sample_config()
            print_success(f"Config sample dibuat di {path}")
            print_info("Edit file tersebut untuk menambah/mengubah profile groups.")
    elif choice == "show_path":
        print_info(f"Config path: {CONFIG_FILE}")


def run_interactive():
    """Interactive menu loop with beautiful UI."""

    # Main menu choices with icons
    main_choices = [
        questionary.Choice(
            f"{ICONS['single']} Single Check    Cek satu profil dengan detail",
            value="single",
        ),
        questionary.Choice(
            f"{ICONS['all']} All Checks      Ringkasan multi-profil (parallel)",
            value="all",
        ),
        questionary.Choice(
            f"{ICONS['arbel']} Arbel Check     Backup & RDS untuk AryaNoble",
            value="arbel",
        ),
        questionary.Choice(
            f"{ICONS['cost']} Cost Report     CloudWatch cost & usage",
            value="cw_cost",
        ),
        questionary.Choice(
            f"{ICONS['settings']} Settings        Konfigurasi & info",
            value="settings",
        ),
        questionary.Choice(f"{ICONS['exit']} Exit", value="exit"),
    ]

    # Check icons mapping
    check_choices = [
        questionary.Choice(f"{ICONS['health']} Health Events", value="health"),
        questionary.Choice(f"{ICONS['cost']} Cost Anomalies", value="cost"),
        questionary.Choice(
            f"{ICONS['guardduty']} GuardDuty Findings", value="guardduty"
        ),
        questionary.Choice(
            f"{ICONS['cloudwatch']} CloudWatch Alarms", value="cloudwatch"
        ),
        questionary.Choice(
            f"{ICONS['notifications']} Notifications", value="notifications"
        ),
        questionary.Choice(f"{ICONS['backup']} Backup Status", value="backup"),
        questionary.Choice(f"{ICONS['rds']} RDS Metrics", value="rds"),
        questionary.Choice(f"{ICONS['ec2list']} EC2 List", value="ec2list"),
    ]

    while True:
        console.clear()
        print_banner()

        main_choice = _select_prompt(f"{ICONS['star']} Menu Utama", main_choices)

        if not main_choice or main_choice == "exit":
            console.print(f"\n[bold green]{ICONS['exit']} Sampai jumpa![/bold green]\n")
            break

        if main_choice == "settings":
            run_settings_menu()
            _pause()
            continue

        if main_choice == "arbel":
            run_arbel_check()
            _pause()
            continue

        if main_choice == "cw_cost":
            run_cloudwatch_cost_report()
            _pause()
            continue

        if main_choice == "single":
            print_mini_banner()
            print_section_header("Single Check", ICONS["single"])

            check = _select_prompt(f"{ICONS['single']} Pilih Check", check_choices)
            if not check:
                continue

            allow_multi = check in ["backup", "rds"]
            profiles, group_choice, back = _pick_profiles(allow_multiple=allow_multi)
            if back:
                continue
            if not profiles:
                print_error("Tidak ada profil dipilih.")
                _pause()
                continue

            region = _choose_region(profiles)
            if region is None:
                continue

            if check in ["backup", "rds"] and len(profiles) > 1:
                run_group_specific(check, profiles, region, group_name=group_choice)
            elif check in ["cost", "guardduty", "cloudwatch", "notifications"]:
                run_all_checks(
                    profiles,
                    region,
                    group_name=group_choice,
                    exclude_backup_rds=True,
                )
            else:
                run_individual_check(check, profiles[0], region)
            _pause()
            continue

        if main_choice == "all":
            print_mini_banner()
            print_section_header("All Checks", ICONS["all"])

            profiles, group_choice, back = _pick_profiles(allow_multiple=True)
            if back:
                continue
            if not profiles:
                print_error("Tidak ada profil dipilih.")
                _pause()
                continue

            region = _choose_region(profiles)
            if region is None:
                continue

            run_all_checks(
                profiles,
                region,
                group_name=group_choice,
                exclude_backup_rds=True,
            )
            _pause()
            continue
