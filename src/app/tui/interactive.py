"""Interactive menu system for AWS Monitoring Hub."""

import questionary

from src.app.tui import common
from src.app.tui.flows import cloudwatch_cost, customer, dashboard, settings
from src.configs.loader import get_alarm_names_for_profile, load_customer_config
from src.core.runtime.config import AVAILABLE_CHECKS
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


HUAWEI_FIXED_PROFILES = [
    "dh_log-ro",
    "dh_prod_nonerp-ro",
    "afco_prod_erp-ro",
    "afco_dev_erp-ro",
    "dh_prod_network-ro",
    "dh_prod_erp-ro",
    "dh_hris-ro",
    "dh_dev_erp-ro",
    "dh_master-ro",
    "dh_mobileapps-ro",
]
HUAWEI_REGION = "ap-southeast-4"


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
    label_to_profile = {}
    for c in customers:
        try:
            cfg = load_customer_config(c["customer_id"])
            for a in cfg.get("accounts", []):
                profile = a.get("profile")
                if profile:
                    customer_label = c.get("display_name") or c.get("customer_id", "")
                    label = f"{a.get('display_name', profile)} [{customer_label}] ({profile})"
                    all_profiles.append(label)
                    label_to_profile[label] = profile
        except Exception:
            continue

    if not all_profiles:
        print_error("Tidak ada profil ditemukan di customer configs.")
        return [], None, False

    selected_labels = common._searchable_multi_select_prompt(
        f"{ICONS['check']} Pilih Profil (multi-select)",
        all_profiles,
    )
    if not selected_labels:
        return [], "All Customers", False

    selected_profiles = []
    seen_profiles = set()
    for label in selected_labels:
        profile = label_to_profile.get(label)
        if profile and profile not in seen_profiles:
            selected_profiles.append(profile)
            seen_profiles.add(profile)

    return selected_profiles, "All Customers", False


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

    profiles, group_choice, back = _pick_profiles_from_customers()

    if back:
        return
    if not profiles:
        print_error("Tidak ada profil dipilih.")
        return

    region = common._choose_region(profiles)
    if region is None:
        return

    # Build check_kwargs for checks that need extra params
    check_kwargs = None
    if selected_check == "alarm_verification":
        alarm_names = []
        for p in profiles:
            alarm_names.extend(get_alarm_names_for_profile(p))
        check_kwargs = {"alarm_names": alarm_names, "min_duration_minutes": 10}

    if len(profiles) > 1:
        run_group_specific(
            selected_check, profiles, region,
            group_name=group_choice,
            check_kwargs=check_kwargs,
        )
    else:
        run_individual_check(
            selected_check, profiles[0], region,
            check_kwargs=check_kwargs,
        )


def run_huawei_utilization():
    """Run consolidated Huawei ECS utilization over fixed profile set."""
    print_mini_banner()
    print_section_header("Huawei Utilization", ICONS.get("huawei", ICONS["cloudwatch"]))

    huawei_checker = AVAILABLE_CHECKS.get("huawei-ecs-util")
    if huawei_checker is None:
        print_error("Check 'huawei-ecs-util' tidak terdaftar. Periksa runtime config.")
        return

    run_all_checks(
        profiles=HUAWEI_FIXED_PROFILES,
        region=HUAWEI_REGION,
        group_name="Huawei",
        checks_override={"huawei-ecs-util": huawei_checker},
        output_mode="huawei_legacy",
    )


def _run_huawei_menu():
    submenu_choice = common._select_prompt(
        f"{ICONS.get('huawei', ICONS['cloudwatch'])} Huawei Check",
        [
            questionary.Choice("Utilization", value="utilization"),
            questionary.Choice("Back", value="back"),
        ],
    )
    if submenu_choice == "utilization":
        run_huawei_utilization()


def run_interactive():
    main_choices = [
        questionary.Choice(
            f"{ICONS['single']} Quick Check      Cek 1 service spesifik",
            value="quick",
        ),
        questionary.Choice(
            f"{ICONS.get('huawei', ICONS['cloudwatch'])} Huawei Check     ECS CPU/MEM utilization",
            value="huawei_check",
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

        if main_choice == "huawei_check":
            _run_huawei_menu()
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
