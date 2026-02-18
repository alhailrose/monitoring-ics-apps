"""Interactive menu system for AWS Monitoring Hub."""

import questionary

from src.app.tui import common
from src.app.tui.flows import arbel, cloudwatch_cost, dashboard, nabati, settings
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


def _render_single_check_dashboard():
    dashboard.render_single_check_dashboard(_is_dense_mode)


def _render_all_checks_dashboard(profile_count):
    dashboard.render_all_checks_dashboard(profile_count, _is_dense_mode)


def run_cloudwatch_cost_report():
    cloudwatch_cost.run_cloudwatch_cost_report()


def run_arbel_check():
    arbel.run_arbel_check(_is_dense_mode)


def run_nabati_check():
    nabati.run_nabati_check()


def run_settings_menu():
    global _current_ui_mode
    _current_ui_mode = settings.run_settings_menu(_current_ui_mode, UI_MODES)


def run_alarm_verification():
    print_mini_banner()
    print_section_header("Alarm Verification (>10m)", ICONS["alarm"])

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
        run_group_specific(
            "alarm_verification", profiles, region, group_name=group_choice
        )
    else:
        run_individual_check("alarm_verification", profiles[0], region)


def run_interactive():
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

        if main_choice == "arbel":
            run_arbel_check()
            common._pause()
            continue

        if main_choice == "nabati":
            run_nabati_check()
            common._pause()
            continue

        if main_choice == "cw_cost":
            run_cloudwatch_cost_report()
            common._pause()
            continue

        if main_choice == "single":
            print_mini_banner()
            print_section_header("Single Check", ICONS["single"])
            _render_single_check_dashboard()

            check = common._select_prompt(
                f"{ICONS['single']} Pilih Check", check_choices
            )
            if not check:
                continue

            allow_multi = check in ["backup", "daily-arbel"]
            profiles, group_choice, back = common._pick_profiles(
                allow_multiple=allow_multi
            )
            if back:
                continue
            if not profiles:
                print_error("Tidak ada profil dipilih.")
                common._pause()
                continue

            region = common._choose_region(profiles)
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

            common._pause()
            continue

        if main_choice == "all":
            print_mini_banner()
            print_section_header("All Checks", ICONS["all"])

            profiles, group_choice, back = common._pick_profiles(allow_multiple=True)
            if back:
                continue
            if not profiles:
                print_error("Tidak ada profil dipilih.")
                common._pause()
                continue

            _render_all_checks_dashboard(len(profiles))

            region = common._choose_region(profiles)
            if region is None:
                continue

            run_all_checks(
                profiles,
                region,
                group_name=group_choice,
                exclude_backup_rds=True,
            )
            common._pause()
            continue


def run_interactive_v2():
    return run_interactive()
