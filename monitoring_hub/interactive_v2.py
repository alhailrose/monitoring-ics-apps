"""Interactive UI v2.

Migrated shell with denser dashboard presentation.
"""

import sys
from datetime import datetime, timedelta

import boto3
import questionary
from botocore.exceptions import BotoCoreError, ClientError
from rich import box
from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table

from .config import CUSTOM_STYLE
from .config import PROFILE_GROUPS
from .runners import run_all_checks, run_group_specific, run_individual_check
from checks import cloudwatch_cost_report as cw_cost_report
from .ui import (
    ICONS,
    VERSION,
    console,
    print_error,
    print_info,
    print_mini_banner,
    print_section_header,
    print_success,
)
from .interactive import (
    _choose_region,
    _pause,
    _pick_profiles,
    _select_prompt,
    run_nabati_check,
    run_settings_menu,
    _format_cw_plain,
)


MENU_LABELS = {
    "single": "Single Check",
    "all": "All Checks",
    "arbel": "Arbel Check",
    "cw_cost": "Cost Report",
    "nabati": "Nabati Analysis",
    "settings": "Settings",
}


def _render_v2_header():
    now = datetime.now()
    status = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    status.add_column("k", style="dim")
    status.add_column("v")
    status.add_row("UI", "v2")
    status.add_row("Version", VERSION)
    status.add_row("Time", now.strftime("%H:%M WIB"))

    core_menu = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    core_menu.add_column("menu", style="cyan")
    core_menu.add_column("tujuan", style="white")
    core_menu.add_row("Single", "Check detail per akun")
    core_menu.add_row("All", "Ringkasan lintas akun")
    core_menu.add_row("Arbel", "RDS / Alarm / Backup")
    core_menu.add_row("Cost", "CloudWatch cost overview")
    core_menu.add_row("Nabati", "CPU + cost analysis")
    core_menu.add_row("Settings", "Konfigurasi aplikasi")

    nav = Panel(
        core_menu,
        title="🧭 Core Menu",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(0, 1),
    )

    stat_panel = Panel(
        status,
        title="📌 Session",
        border_style="green",
        box=box.ROUNDED,
        padding=(0, 1),
    )

    hint_panel = Panel(
        "↑↓ navigasi  •  Space centang  •  Enter konfirmasi  •  Ctrl+C keluar",
        title="⌨️ Shortcuts",
        border_style="bright_black",
        box=box.ROUNDED,
        padding=(0, 1),
    )

    active = Panel(
        "[bold green]UI v2 AKTIF[/bold green]\n"
        "Mode fokus: hasil check tampil di halaman terpisah.",
        title="🚀 Migrated Mode",
        border_style="green",
        box=box.ROUNDED,
        padding=(0, 1),
    )

    console.print(Columns([nav, stat_panel, active], expand=True))
    console.print(hint_panel)
    console.print()


def _run_focus_action(choice, action):
    label = MENU_LABELS.get(choice, choice)
    started = datetime.now()
    console.clear()
    action()
    elapsed = (datetime.now() - started).total_seconds()
    print_info(f"Selesai {label} dalam {elapsed:.1f} detik")
    _pause()


def _select_main_menu():
    choices = [
        questionary.Choice(f"{ICONS['single']} Single Check", value="single"),
        questionary.Choice(f"{ICONS['all']} All Checks", value="all"),
        questionary.Choice(f"{ICONS['arbel']} Arbel Check", value="arbel"),
        questionary.Choice(f"{ICONS['cost']} Cost Report", value="cw_cost"),
        questionary.Choice(f"{ICONS['nabati']} Nabati Analysis", value="nabati"),
        questionary.Choice(f"{ICONS['settings']} Settings", value="settings"),
        questionary.Choice(f"{ICONS['exit']} Exit", value="exit"),
    ]
    try:
        return questionary.select(
            "Pilih menu",
            choices=choices,
            style=CUSTOM_STYLE,
            instruction="(↑↓ navigasi, Enter pilih)",
        ).ask()
    except KeyboardInterrupt:
        return "exit"


def _multi_select_numbered(title, items, default_selected=None):
    default_selected = set(default_selected or [])
    if not items:
        return []

    try:
        choices = [
            questionary.Choice(item, value=item, checked=(item in default_selected))
            for item in items
        ]
        ans = questionary.checkbox(
            title,
            choices=choices,
            style=CUSTOM_STYLE,
            instruction="(Spasi untuk pilih, Enter konfirmasi)",
        ).ask()
    except KeyboardInterrupt:
        return []
    return ans or []


def _select_check_menu():
    choices = [
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
    try:
        return questionary.select(
            f"{ICONS['single']} Pilih Check",
            choices=choices,
            style=CUSTOM_STYLE,
            instruction="(↑↓ navigasi, Enter pilih)",
        ).ask()
    except KeyboardInterrupt:
        return None


def _run_single_check_v2():
    print_mini_banner()
    print_section_header("Single Check (UI v2)", ICONS["single"])

    check = _select_check_menu()
    if not check:
        return

    allow_multi = check in ["backup", "daily-arbel"]
    profiles, group_choice, back = _pick_profiles(allow_multiple=allow_multi)
    if back:
        return
    if not profiles:
        print_error("Tidak ada profil dipilih.")
        return

    region = _choose_region(profiles)
    if region is None:
        return

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


def _run_all_checks_v2():
    print_mini_banner()
    print_section_header("All Checks (UI v2)", ICONS["all"])

    profiles, group_choice, back = _pick_profiles(allow_multiple=True)
    if back:
        return
    if not profiles:
        print_error("Tidak ada profil dipilih.")
        return

    region = _choose_region(profiles)
    if region is None:
        return

    run_all_checks(
        profiles,
        region,
        group_name=group_choice,
        exclude_backup_rds=True,
    )


def _run_cloudwatch_cost_report_v2():
    print_mini_banner()
    print_section_header("CloudWatch Cost Report (UI v2)", ICONS["cost"])
    console.print(
        Panel(
            "Ringkasan biaya CloudWatch lintas akun.\n"
            "Source profile: [bold]ksni-master[/bold] (NABATI-KSNI)",
            title="📉 Cost Scope",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )

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

    try:
        top_str = questionary.text(
            "Top berapa akun?", default="10", style=CUSTOM_STYLE
        ).ask()
        top_n = int(top_str) if top_str else 10
    except Exception:
        top_n = 10

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
    else:
        text = _format_cw_plain(
            rows, names, start.isoformat(), end.isoformat(), region, top_n
        )
        console.print(
            Panel(text, title="[bold]Cost Report[/bold]", border_style="cyan")
        )


def _run_arbel_check_v2():
    print_mini_banner()
    print_section_header("Arbel Check (UI v2)", ICONS["arbel"])

    arbel_profiles = [
        "connect-prod",
        "cis-erha",
        "dermies-max",
        "erha-buddy",
        "public-web",
    ]
    default_profiles = {"dermies-max", "cis-erha", "connect-prod"}
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

    overview = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    overview.add_column("k", style="dim")
    overview.add_column("v")
    overview.add_row("Region", "ap-southeast-3")
    overview.add_row("Default Accounts", ", ".join(sorted(default_profiles)))
    overview.add_row("Rule", "report jika ALARM >= 10 menit")
    console.print(
        Panel(overview, title="🏥 Arbel Scope", border_style="cyan", box=box.ROUNDED)
    )

    arbel_choices = [
        questionary.Choice("🗄️ RDS Monitoring", value="rds"),
        questionary.Choice("⏱️ Alarm Verification", value="alarm"),
        questionary.Choice("💵 Daily Budget", value="budget"),
        questionary.Choice(f"{ICONS['backup']} Backup", value="backup"),
    ]
    mode = _select_prompt(f"{ICONS['arbel']} Pilih Mode Operasi", arbel_choices)
    if not mode:
        return

    if mode == "backup":
        profiles = list(PROFILE_GROUPS["Aryanoble"].keys())
        run_group_specific("backup", profiles, "ap-southeast-3", group_name="Aryanoble")
        return

    selected_profiles = _multi_select_numbered(
        "Pilih akun Arbel",
        arbel_profiles,
        default_selected=default_profiles,
    )
    if not selected_profiles:
        print_error("Tidak ada akun dipilih.")
        return

    if mode == "alarm":
        alarm_names = []
        seen = set()
        for profile in selected_profiles:
            for alarm in arbel_alarm_catalog.get(profile, []):
                if alarm in seen:
                    continue
                seen.add(alarm)
                alarm_names.append(alarm)
        if not alarm_names:
            print_error("Tidak ada alarm catalog untuk akun terpilih.")
            return

        selected_alarm_names = _multi_select_numbered(
            "Pilih nama alarm",
            alarm_names,
            default_selected=set(alarm_names),
        )
        if not selected_alarm_names:
            print_error("Nama alarm wajib dipilih.")
            return

        run_group_specific(
            "alarm_verification",
            selected_profiles,
            "ap-southeast-3",
            group_name="Aryanoble Alarm",
            check_kwargs={
                "alarm_names": selected_alarm_names,
                "min_duration_minutes": 10,
            },
        )
        return

    if mode == "budget":
        run_group_specific(
            "daily-budget",
            selected_profiles,
            "ap-southeast-3",
            group_name="Aryanoble Budget",
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
        "ap-southeast-3",
        group_name=f"Aryanoble ({suffix})",
        check_kwargs={"window_hours": window_hours},
    )


def run_interactive_v2():
    """Run migrated interactive UI v2 shell."""
    while True:
        console.clear()
        _render_v2_header()
        choice = _select_main_menu()

        if not choice or choice == "exit":
            print_success("Keluar dari UI v2. Sampai jumpa!")
            sys.exit(0)

        if choice == "single":
            _run_focus_action(choice, _run_single_check_v2)
            continue

        if choice == "all":
            _run_focus_action(choice, _run_all_checks_v2)
            continue

        if choice == "arbel":
            _run_focus_action(choice, _run_arbel_check_v2)
            continue

        if choice == "cw_cost":
            _run_focus_action(choice, _run_cloudwatch_cost_report_v2)
            continue

        if choice == "nabati":
            _run_focus_action(choice, run_nabati_check)
            continue

        if choice == "settings":
            _run_focus_action(choice, run_settings_menu)
