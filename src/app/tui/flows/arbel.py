"""Arbel check interactive flow."""

import questionary
from rich import box
from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table

from src.app.tui import common
from src.configs.loader import load_customer_config
from src.core.runtime.config import PROFILE_GROUPS, CUSTOM_STYLE
from src.core.runtime.runners import run_group_specific
from src.core.runtime.ui import (
    console,
    print_error,
    print_mini_banner,
    print_section_header,
    ICONS,
)


def run_arbel_check(is_dense_mode):
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

    def _load_alarm_catalog():
        """Build alarm catalog from aryanoble.yaml alarm_names per account."""
        catalog: dict[str, list[str]] = {}
        try:
            cfg = load_customer_config("aryanoble")
            for account in cfg.get("accounts", []):
                profile = account.get("profile", "")
                alarm_names = account.get("alarm_names", [])
                if profile and alarm_names:
                    catalog[profile] = list(alarm_names)
        except Exception:
            pass
        return catalog

    arbel_alarm_catalog = _load_alarm_catalog()

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

        if is_dense_mode():
            flow_panel = Panel(
                "[bold cyan]RDS Monitoring[/bold cyan]\nPilih akun lalu window 1h / 3h / 12h\n\n"
                "[bold cyan]Alarm Verification[/bold cyan]\nPilih akun lalu alarm yang mau dicek\n\n"
                "[bold cyan]Backup[/bold cyan]\nLaporan backup semua akun Arbel",
                title="⚙️ Flow Utama",
                border_style="cyan",
                box=box.ROUNDED,
                padding=(1, 2),
            )
            scope_panel = Panel(
                top,
                title="📌 Scope",
                border_style="green",
                box=box.ROUNDED,
                padding=(1, 2),
            )
            mode_panel = Panel(
                mode,
                title="🧭 Steps",
                border_style="magenta",
                box=box.ROUNDED,
                padding=(1, 2),
            )
            console.print(Columns([flow_panel, scope_panel, mode_panel], expand=True))
        else:
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
            questionary.Choice(
                profile, value=profile, checked=(profile in default_profiles)
            )
            for profile in arbel_profiles
        ]
        selected = common._checkbox_prompt(
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
                questionary.Choice(alarm_name, value=alarm_name, checked=False)
                for alarm_name in candidate_alarm_names
            ]
            selected_alarm_names = common._checkbox_prompt(
                f"{ICONS['alarm']} Pilih nama alarm",
                alarm_choices,
            )
            return selected_alarm_names or []

        try:
            alarm_input = questionary.text(
                "Masukkan nama alarm (pisahkan dengan koma jika lebih dari 1):",
                style=CUSTOM_STYLE,
            ).ask()
        except KeyboardInterrupt:
            common._handle_interrupt(exit_direct=True)
            return []
        return [x.strip() for x in (alarm_input or "").split(",") if x.strip()]

    _render_arbel_dashboard()

    arbel_choices = [
        questionary.Choice("🗄️ RDS Monitoring", value="rds"),
        questionary.Choice("⏱️ Alarm Verification", value="alarm-name"),
        questionary.Choice("💵 Daily Budget", value="budget"),
        questionary.Choice(f"{ICONS['backup']} Backup", value="backup"),
    ]

    choice = common._select_prompt(
        f"{ICONS['arbel']} Pilih Mode Operasi", arbel_choices
    )
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

    if choice == "budget":
        run_group_specific(
            "daily-budget",
            selected_profiles,
            region,
            group_name="Aryanoble Budget",
        )
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
    selected_window = common._select_prompt(
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
