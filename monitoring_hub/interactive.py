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
        mandatory_groups = {"NABATI-KSNI", "Master"}
        group_choices = [
            questionary.Choice(
                f"{ICONS['dot']} {name} ({len(profs)} profiles){' (mandatory)' if name in mandatory_groups else ''}",
                value=name,
            )
            for name, profs in PROFILE_GROUPS.items()
        ]

        group_choice = _select_prompt(f"{ICONS['all']} Pilih Group", group_choices)
        if not group_choice:
            return [], None, True

        choices = list(PROFILE_GROUPS[group_choice].keys())
        # Mark mandatory profiles
        mandatory_profiles = {"asg"}
        if allow_multiple:
            # Add select all option
            formatted_choices = [
                f"{choice} (mandatory)" if choice in mandatory_profiles else choice
                for choice in choices
            ]
            profiles = _checkbox_prompt(
                f"{ICONS['check']} Pilih Akun dari {group_choice}", formatted_choices
            )
            profiles = profiles or []
            # Remove (mandatory) suffix from selected profiles
            profiles = [p.replace(" (mandatory)", "") for p in profiles]
        else:
            formatted_choices = [
                f"{choice} (mandatory)" if choice in mandatory_profiles else choice
                for choice in choices
            ]
            selected = _select_prompt(
                f"{ICONS['single']} Pilih Akun", formatted_choices
            )
            profiles = [selected.replace(" (mandatory)", "")] if selected else []
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


def _render_main_dashboard():
    """Render compact top bar for main menu."""
    quick = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    quick.add_column("k", style="dim")
    quick.add_column("v")
    quick.add_row("Core", "Single Check  |  All Checks  |  Arbel Check")
    quick.add_row("Support", "Cost Report  |  Settings")
    quick.add_row("Keys", "↑↓ navigate  •  Enter select  •  Ctrl+C exit")

    console.print(
        Panel(
            quick,
            title="🧭 Control Center",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(0, 1),
        )
    )
    console.print()


def _render_single_check_dashboard():
    """Render compact single-check helper."""
    console.print(
        Panel(
            f"{ICONS['health']} Health  •  {ICONS['guardduty']} GuardDuty  •  {ICONS['cloudwatch']} CloudWatch  •  "
            f"{ICONS['backup']} Backup  •  {ICONS['rds']} Daily Arbel  •  {ICONS['alarm']} Alarm  •  "
            f"{ICONS['cost']} Cost  •  {ICONS['notifications']} Notifications  •  {ICONS['ec2list']} EC2 List",
            title="🔍 Available Checks",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(0, 1),
        )
    )
    console.print()


def _render_all_checks_dashboard(profile_count: int):
    """Render compact all-checks helper."""
    console.print(
        Panel(
            f"Target: [bold]{profile_count} akun[/bold]  •  Mode: parallel  •  Focus: Cost / GuardDuty / CloudWatch / Notifications",
            title="📋 All Checks Plan",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(0, 1),
        )
    )
    console.print()


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
    console.print(
        Panel(
            "[bold]Tujuan:[/bold] ringkasan biaya CloudWatch lintas akun\n"
            "[bold]Output:[/bold] table / markdown / plain text\n"
            "[bold yellow]Scope:[/bold yellow] source profile tetap [bold]ksni-master[/bold] (NABATI-KSNI)",
            title="📉 Cost Dashboard",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )
    console.print()

    profile = "ksni-master"
    print_info(f"Source profile cost report: {profile} (NABATI-KSNI)")
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
    """Run Arbel-specific checks with clearer account/alarm selection."""
    print_mini_banner()
    print_section_header("Arbel Check (RDS Utilization)", ICONS["arbel"])

    arbel_profiles = [
        "connect-prod",
        "cis-erha",
        "dermies-max",
        "erha-buddy",
        "public-web",
    ]
    default_profiles = ["dermies-max", "cis-erha", "connect-prod"]
    arbel_alarm_catalog = {
        "connect-prod": [
            "noncis-prod-rds-acu-alarm",
            "noncis-prod-rds-cpu-alarm",
            "noncis-prod-rds-freeable-memory-alarm",
            "noncis-prod-rds-databaseconnections-cluster-alarm",
        ],
        "cis-erha": [
            "cis-prod-rds-acu-writer-alarm",
            "cis-prod-rds-cpu-writer-alarm",
            "cis-prod-rds-memory-writer-alarm",
            "cis-prod-rds-connection-writer-alarm",
            "cis-prod-rds-acu-reader-alarm",
            "cis-prod-rds-cpu-reader-alarm",
            "cis-prod-rds-memory-reader-alarm",
            "cis-prod-rds-connection-reader-alarm",
        ],
        "dermies-max": [
            "dermies-prod-rds-writer-acu-alarm",
            "dermies-prod-rds-writer-cpu-alarm",
            "dermies-prod-rds-writer-freeable-memory-alarm",
            "dermies-prod-rds-writer-connections-alarm",
            "dermies-prod-rds-reader-acu-alarm",
            "dermies-prod-rds-reader-cpu-alarm",
            "dermies-prod-rds-reader-freeable-memory-alarm",
            "dermies-prod-rds-reader-connections-alarm",
        ],
        "erha-buddy": [
            "erhabuddy-prod-rds-cpu-alarm",
            "erhabuddy-prod-rds-connections-alarm",
            "erhabuddy-prod-rds-freeable-memory-alarm",
        ],
    }

    def _render_arbel_dashboard():
        default_alarm_count = sum(
            len(arbel_alarm_catalog.get(profile, [])) for profile in default_profiles
        )

        top = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        top.add_column("k", style="dim")
        top.add_column("v")
        top.add_row("Region", "ap-southeast-3")
        top.add_row("Default Accounts", ", ".join(default_profiles))
        top.add_row("Default Alarm Count", str(default_alarm_count))
        top.add_row("Rule", "report jika ALARM >= 10 menit")

        mode = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        mode.add_column("mode", style="cyan")
        mode.add_column("flow", style="white")
        mode.add_row("RDS Monitoring", "pilih akun -> pilih window -> run")
        mode.add_row("Alarm Verification", "pilih akun -> pilih alarm -> run")
        mode.add_row("Backup", "langsung run semua akun Aryanoble")

        console.print(
            Panel(
                top,
                title="🏥 Arbel Monitoring Center",
                border_style="cyan",
                box=box.ROUNDED,
                padding=(0, 1),
            )
        )
        console.print(
            Panel(
                mode,
                title="🧭 Flow",
                border_style="green",
                box=box.ROUNDED,
                padding=(0, 1),
            )
        )
        console.print()

    def _pick_arbel_profiles():
        profile_choices = [
            questionary.Choice(p, value=p, checked=(p in default_profiles))
            for p in arbel_profiles
        ]
        selected = _checkbox_prompt(
            f"{ICONS['check']} Pilih akun Arbel (default sudah tercentang)",
            profile_choices,
        )
        return selected or []

    def _collect_alarm_names(selected_profiles):
        candidate_alarm_names = []
        seen_alarm_names = set()
        for profile in selected_profiles:
            for alarm_name in arbel_alarm_catalog.get(profile, []):
                if alarm_name in seen_alarm_names:
                    continue
                seen_alarm_names.add(alarm_name)
                candidate_alarm_names.append(alarm_name)

        if candidate_alarm_names:
            alarm_choices = [
                questionary.Choice(alarm_name, value=alarm_name, checked=True)
                for alarm_name in candidate_alarm_names
            ]
            selected_alarm_names = _checkbox_prompt(
                f"{ICONS['alarm']} Pilih nama alarm (default semua tercentang)",
                alarm_choices,
            )
            return selected_alarm_names or []

        try:
            alarm_input = questionary.text(
                "Masukkan nama alarm (pisahkan dengan koma jika lebih dari 1):",
                style=CUSTOM_STYLE,
            ).ask()
        except KeyboardInterrupt:
            _handle_interrupt(exit_direct=True)
            return []
        return [x.strip() for x in (alarm_input or "").split(",") if x.strip()]

    _render_arbel_dashboard()

    arbel_choices = [
        questionary.Choice("🗄️ RDS Monitoring", value="rds"),
        questionary.Choice("⏱️ Alarm Verification", value="alarm-name"),
        questionary.Choice(f"{ICONS['backup']} Backup", value="backup"),
    ]

    choice = _select_prompt(f"{ICONS['arbel']} Pilih Mode Operasi", arbel_choices)
    if not choice:
        return

    region = "ap-southeast-3"

    if choice == "backup":
        profiles = list(PROFILE_GROUPS["Aryanoble"].keys())
        run_group_specific("backup", profiles, region, group_name="Aryanoble")
        return

    selected_profiles = _pick_arbel_profiles()
    if not selected_profiles:
        print_error("Tidak ada akun dipilih.")
        return

    if choice == "alarm-name":
        alarm_names = _collect_alarm_names(selected_profiles)
        if not alarm_names:
            print_error("Nama alarm wajib diisi.")
            return

        run_group_specific(
            "alarm_verification",
            selected_profiles,
            region,
            group_name="Aryanoble Alarm",
            check_kwargs={
                "alarm_names": alarm_names,
                "min_duration_minutes": 10,
            },
        )
        return

    window_choices = [
        questionary.Choice("1 Jam", value=(1, "1 Hour")),
        questionary.Choice("3 Jam", value=(3, "3 Hours")),
        questionary.Choice("12 Jam", value=(12, "12 Hours")),
    ]
    selected_window = _select_prompt(
        f"{ICONS['rds']} Pilih Window RDS", window_choices, default=(3, "3 Hours")
    )
    if not selected_window:
        return

    window_hours, suffix = selected_window

    run_group_specific(
        "daily-arbel",
        selected_profiles,
        region,
        group_name=f"Aryanoble ({suffix})",
        check_kwargs={"window_hours": window_hours},
    )


def run_nabati_check():
    """Run Nabati-specific analysis (CPU usage + Cost for NABATI-KSNI accounts)."""
    from checks.nabati_analysis import run_nabati_analysis

    print_mini_banner()
    print_section_header("Nabati Analysis", ICONS["nabati"])

    # Ask for month
    now = datetime.now()
    current_month = now.strftime("%Y-%m")

    month_input = questionary.text(
        f"{ICONS['info']} Bulan analisis (YYYY-MM, default: {current_month}):",
        default=current_month,
        style=CUSTOM_STYLE,
    ).ask()

    if not month_input:
        return

    month = month_input.strip() or current_month

    # Get all Nabati profiles
    profiles = list(PROFILE_GROUPS["NABATI-KSNI"].keys())

    print_info(f"Menganalisis {len(profiles)} akun Nabati untuk bulan {month}...")

    with console.status("[bold cyan]Mengumpulkan data CPU & Cost...", spinner="dots"):
        results = run_nabati_analysis(profiles, month)

    # Display results
    _display_nabati_results(results)


def _display_nabati_results(data: dict):
    """Display Nabati analysis results in formatted tables."""
    results = data["results"]
    month = data["month"]

    # Separate high and low CPU
    high_cpu = []
    low_cpu = []
    total_cost = 0.0

    for r in results:
        if "error" in r:
            continue

        total_cost += r.get("cost", 0.0)

        if r.get("no_instances"):
            low_cpu.append(r)
        elif r.get("max_cpu", 0) >= 80:
            high_cpu.append(r)
        else:
            low_cpu.append(r)

    # High CPU table
    console.print()
    console.print(f"[bold cyan]Instances with spikes ≥80% ({month})[/bold cyan]")

    if high_cpu:
        high_table = Table(box=box.ROUNDED, show_header=True)
        high_table.add_column("Account", style="cyan")
        high_table.add_column("Account ID", style="dim")
        high_table.add_column("Instance", style="yellow")
        high_table.add_column("Max CPU", style="red bold")
        high_table.add_column("Time", style="dim")

        for r in sorted(high_cpu, key=lambda x: x.get("max_cpu", 0), reverse=True):
            high_table.add_row(
                r["account_name"],
                r["profile"].split("-")[0] if "-" in r["profile"] else r["profile"],
                r.get("max_cpu_instance", "N/A"),
                f"{r.get('max_cpu', 0):.1f}%",
                r.get("max_cpu_time", "N/A"),
            )

        console.print(high_table)
    else:
        console.print("[dim]None[/dim]")

    # Low CPU table
    console.print()
    console.print(f"[bold cyan]Instances with no spikes ≥80% ({month})[/bold cyan]")

    if low_cpu:
        low_table = Table(box=box.ROUNDED, show_header=True)
        low_table.add_column("Account", style="cyan")
        low_table.add_column("Status", style="green")
        low_table.add_column("Max CPU", style="yellow")

        for r in sorted(low_cpu, key=lambda x: x["account_name"]):
            if r.get("no_instances"):
                status = "No instances running"
                cpu = "N/A"
            else:
                status = f"Instance {r.get('max_cpu_instance', 'N/A')}"
                cpu = f"{r.get('max_cpu', 0):.1f}%"

            low_table.add_row(r["account_name"], status, cpu)

        console.print(low_table)

    # Cost table
    console.print()
    console.print(f"[bold cyan]Total Cost - {month}[/bold cyan]")

    cost_table = Table(box=box.ROUNDED, show_header=True)
    cost_table.add_column("Account", style="cyan")
    cost_table.add_column("Cost (USD)", style="green", justify="right")

    for r in sorted(results, key=lambda x: x.get("cost", 0), reverse=True):
        if "error" not in r:
            cost_table.add_row(
                r["account_name"],
                f"${r.get('cost', 0):,.2f}",
            )

    cost_table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]${total_cost:,.2f}[/bold]",
    )

    console.print(cost_table)
    console.print()


def run_settings_menu():
    """Settings and configuration menu."""
    print_mini_banner()
    print_section_header("Settings & Info", ICONS["settings"])
    console.print(
        Panel(
            "Kelola config default region, workers, dan profile groups.\n"
            "Gunakan sample config untuk bootstrap environment baru.",
            title="⚙️ Configuration Center",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )
    console.print()

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


def run_alarm_verification():
    """Run Alarm Verification check."""
    print_mini_banner()
    print_section_header("Alarm Verification (>10m)", ICONS["alarm"])

    # 1. Pilih Profil
    profiles, group_choice, back = _pick_profiles(allow_multiple=True)
    if back:
        return
    if not profiles:
        print_error("Tidak ada profil dipilih.")
        return

    # 2. Pilih Region
    region = _choose_region(profiles)
    if region is None:
        return

    # 3. Jalankan Check
    if len(profiles) > 1:
        run_group_specific(
            "alarm_verification", profiles, region, group_name=group_choice
        )
    else:
        run_individual_check("alarm_verification", profiles[0], region)


def run_interactive():
    """Interactive menu loop with beautiful UI."""

    # ... (rest of the function)

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
        questionary.Choice(f"{ICONS['rds']} Daily Arbel", value="daily-arbel"),
        questionary.Choice(
            f"{ICONS['alarm']} Alarm Verification (>10m)", value="alarm_verification"
        ),
        questionary.Choice(f"{ICONS['ec2list']} EC2 List", value="ec2list"),
    ]

    while True:
        console.clear()
        print_banner()
        _render_main_dashboard()

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

        if main_choice == "nabati":
            run_nabati_check()
            _pause()
            continue

        if main_choice == "cw_cost":
            run_cloudwatch_cost_report()
            _pause()
            continue

        if main_choice == "single":
            print_mini_banner()
            print_section_header("Single Check", ICONS["single"])
            _render_single_check_dashboard()

            check = _select_prompt(f"{ICONS['single']} Pilih Check", check_choices)
            if not check:
                continue

            allow_multi = check in ["backup", "daily-arbel"]
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

            if check in ["backup", "daily-arbel"] and len(profiles) > 1:
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

            _render_all_checks_dashboard(len(profiles))

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
