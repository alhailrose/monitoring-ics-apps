"""Interactive menu system for AWS Monitoring Hub."""

import questionary

from src.app.tui import common
from src.app.tui.flows import cloudwatch_cost, customer, dashboard, settings
from src.configs.loader import load_customer_config
from src.core.runtime.runners import (
    run_all_checks,
    run_group_specific,
    run_individual_check,
)
from src.core.runtime.ui import (
    console,
    print_banner,
    print_error,
    print_mini_banner,
    print_section_header,
    ICONS,
)


UI_MODES = {
    "dense": "Dense Ops",
    "compact": "Compact",
}
_current_ui_mode = "compact"


def _is_dense_mode():
    return _current_ui_mode == "dense"


_handle_interrupt = common._handle_interrupt
_select_prompt = common._select_prompt
_checkbox_prompt = common._checkbox_prompt
_choose_region = common._choose_region
_pick_profiles = common._pick_profiles
_pause = common._pause


def _render_main_dashboard():
    dashboard.render_main_dashboard(_is_dense_mode, _current_ui_mode, UI_MODES)


def _render_all_checks_dashboard(profile_count):
    dashboard.render_all_checks_dashboard(profile_count, _is_dense_mode)


def run_cloudwatch_cost_report():
    cloudwatch_cost.run_cloudwatch_cost_report()


def run_customer_report():
    customer.run_customer_report()


def run_aryanoble():
    """Run Aryanoble sub-flow directly from main menu."""
    try:
        cfg = load_customer_config("aryanoble")
    except Exception as exc:
        print_error(f"Gagal load config aryanoble: {exc}")
        return
    customer._run_aryanoble_subflow(cfg)


def run_settings_menu():
    global _current_ui_mode
    _current_ui_mode = settings.run_settings_menu(_current_ui_mode, UI_MODES)


CHECK_CHOICES = [
    questionary.Choice(f"{ICONS['health']} Health Events", value="health"),
    questionary.Choice(f"{ICONS['cost']} Cost Anomalies", value="cost"),
    questionary.Choice(f"{ICONS['guardduty']} GuardDuty Findings", value="guardduty"),
    questionary.Choice(f"{ICONS['cloudwatch']} CloudWatch Alarms", value="cloudwatch"),
    questionary.Choice(f"{ICONS['notifications']} Notifications", value="notifications"),
    questionary.Choice(f"{ICONS['backup']} Backup Status", value="backup"),
    questionary.Choice(f"{ICONS['alarm']} Alarm Verification (>10m)", value="alarm_verification"),
    questionary.Choice(f"{ICONS['ec2list']} EC2 List", value="ec2list"),
]


def _pick_profiles_from_customers():
    """Pick profiles from all customer configs, multi-select."""
    from src.configs.loader import list_customers, load_customer_config

    customers = list_customers()
    if not customers:
        print_error("Tidak ada customer config ditemukan.")
        return [], None, False

    all_profiles = []
    for c in customers:
        try:
            cfg = load_customer_config(c["customer_id"])
            for a in cfg.get("accounts", []):
                profile = a.get("profile")
                if profile:
                    label = f"{a.get('display_name', profile)} [{c['display_name']}]"
                    all_profiles.append((label, profile))
        except Exception:
            continue

    if not all_profiles:
        print_error("Tidak ada profil ditemukan di customer configs.")
        return [], None, False

    choices = [
        questionary.Choice(label, value=profile, checked=True)
        for label, profile in all_profiles
    ]
    selected = common._checkbox_prompt(
        f"{ICONS['check']} Pilih Profil (multi-select)", choices
    )
    return selected or [], "All Customers", False


def _run_quick_check():
    """Quick Check flow: pick 1 check + profiles, run."""
    print_mini_banner()
    print_section_header("Quick Check", ICONS["single"])

    # Pick 1 check
    selected_check = common._select_prompt(
        f"{ICONS['single']} Pilih Check", CHECK_CHOICES
    )
    if not selected_check:
        return

    # Pick profile source: All Customer or Local
    source_choices = [
        questionary.Choice(
            f"{ICONS['star']} All Customer - Profil dari customer configs", value="customer"
        ),
        questionary.Choice(
            f"{ICONS['ec2list']} Local Profiles - AWS CLI config", value="local"
        ),
    ]
    source = common._select_prompt(f"{ICONS['settings']} Sumber Profil", source_choices)
    if not source:
        return

    if source == "customer":
        profiles, group_choice, back = _pick_profiles_from_customers()
    else:
        profiles, group_choice, back = common._pick_profiles(allow_multiple=True)

    if back:
        return
    if not profiles:
        print_error("Tidak ada profil dipilih.")
        return

    region = common._choose_region(profiles)
    if region is None:
        return

    if len(profiles) > 1:
        run_group_specific(selected_check, profiles, region, group_name=group_choice)
    else:
        run_individual_check(selected_check, profiles[0], region)


def run_interactive():
    main_choices = [
        questionary.Choice(
            f"{ICONS['single']} Quick Check      Cek 1 service spesifik",
            value="quick",
        ),
        questionary.Choice(
            f"{ICONS['arbel']} Aryanoble        RDS / Alarm / Budget / Backup",
            value="aryanoble",
        ),
        questionary.Choice(
            f"{ICONS['all']} Customer Report  Daily monitoring report per customer",
            value="customer",
        ),
        questionary.Choice(
            f"{ICONS['cost']} Cost Report      CloudWatch cost & usage",
            value="cw_cost",
        ),
        questionary.Choice(
            f"{ICONS['settings']} Settings         Konfigurasi & info",
            value="settings",
        ),
        questionary.Choice(f"{ICONS['exit']} Exit", value="exit"),
    ]

    while True:
        console.clear()
        print_banner(show_tips=False)
        _render_main_dashboard()

        main_choice = common._select_prompt(f"{ICONS['star']} Menu Utama", main_choices)

        if not main_choice or main_choice == "exit":
            console.print(f"\n[bold green]{ICONS['exit']} Sampai jumpa![/bold green]\n")
            break

        if main_choice == "settings":
            run_settings_menu()
            common._pause()
            continue

        if main_choice == "customer":
            run_customer_report()
            common._pause()
            continue

        if main_choice == "aryanoble":
            run_aryanoble()
            common._pause()
            continue

        if main_choice == "cw_cost":
            run_cloudwatch_cost_report()
            common._pause()
            continue

        if main_choice == "quick":
            _run_quick_check()
            common._pause()
            continue


def run_interactive_v2():
    return run_interactive()
