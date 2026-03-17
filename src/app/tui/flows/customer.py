"""Customer Report interactive flow.

Pilih customer -> jalankan checks dari YAML -> Slack prompt.
Aryanoble punya sub-flow khusus (RDS/Alarm/Budget/Backup).
"""

import questionary
from rich import box
from rich.panel import Panel
from rich.table import Table

from src.app.tui import common
from src.configs.loader import (
    get_alarm_names_for_profile,
    list_customers,
    load_customer_config,
)
from src.core.runtime.config import AVAILABLE_CHECKS
from src.core.runtime.runners import run_all_checks, run_group_specific
from src.core.runtime.ui import (
    console,
    print_error,
    print_info,
    print_mini_banner,
    print_section_header,
    ICONS,
)


def _render_customer_dashboard(customers):
    """Show customer overview panel."""
    table = Table(box=box.SIMPLE, show_header=True, padding=(0, 1))
    table.add_column("Customer", style="cyan")
    table.add_column("Accounts", style="white", justify="right")
    table.add_column("Checks", style="yellow")
    table.add_column("Slack", style="white")

    for c in customers:
        slack_status = (
            "[green]ON[/green]" if c.get("slack_enabled") else "[dim]off[/dim]"
        )
        checks_list = c.get("checks", [])

        # Show all checks if <= 4, otherwise show first 3 + count
        if len(checks_list) <= 4:
            checks_str = ", ".join(checks_list) if checks_list else "[dim]none[/dim]"
        else:
            checks_str = (
                ", ".join(checks_list[:3]) + f" [dim]+{len(checks_list) - 3} more[/dim]"
            )

        table.add_row(
            c["display_name"],
            str(c["account_count"]),
            checks_str,
            slack_status,
        )

    console.print(
        Panel(
            table,
            title=f"{ICONS['star']} Customer Overview",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(0, 1),
        )
    )
    console.print()


def _render_breadcrumb(path: str):
    """Render lightweight location hint for current menu step."""
    console.print(f"[dim]Path: {path}[/dim]")


def _build_profile_regions(accounts, selected_profiles):
    """Build {profile: [regions...]} from customer accounts.

    Supports:
    - account.region: "ap-southeast-3"
    - account.regions: ["ap-southeast-1", "eu-central-1", ...]
    """
    selected = set(selected_profiles or [])
    mapping = {}
    for account in accounts or []:
        profile = account.get("profile")
        if not profile or profile not in selected:
            continue

        regions = []
        raw_regions = account.get("regions")
        if isinstance(raw_regions, list):
            regions = [str(r).strip() for r in raw_regions if str(r).strip()]
        elif isinstance(raw_regions, str) and raw_regions.strip():
            regions = [raw_regions.strip()]
        elif account.get("region"):
            regions = [str(account.get("region")).strip()]

        if regions:
            mapping[profile] = regions

    return mapping


def _run_aryanoble_subflow(cfg):
    """Aryanoble-specific sub-flow: RDS Monitoring / Alarm Verification / Budget / Backup.

    Escape at any step goes back to previous step.
    """
    arbel_profiles = [
        a["profile"] for a in cfg.get("accounts", []) if a.get("daily_arbel")
    ]
    ec2_profiles = []
    for account in cfg.get("accounts", []):
        profile = account.get("profile")
        daily = account.get("daily_arbel") or {}
        has_primary_ec2 = isinstance(daily, dict) and daily.get("service_type") == "ec2"
        has_extra_ec2 = bool(account.get("daily_arbel_extra"))
        if profile and (has_primary_ec2 or has_extra_ec2):
            ec2_profiles.append(profile)
    all_profiles = [a["profile"] for a in cfg.get("accounts", [])]
    default_rds_profiles = ["dermies-max", "cis-erha", "connect-prod"]

    def _load_alarm_catalog():
        """Build alarm catalog from aryanoble.yaml alarm_names per account."""
        catalog: dict[str, list[str]] = {}
        try:
            for account in cfg.get("accounts", []):
                profile = account.get("profile", "")
                alarm_names = account.get("alarm_names", [])
                if profile and alarm_names:
                    catalog[profile] = list(alarm_names)
        except Exception:
            pass
        return catalog

    arbel_alarm_catalog = _load_alarm_catalog()

    def _parse_alarm_input(raw: str) -> list[str]:
        tokens = str(raw or "").replace("\n", ",").split(",")
        alarms = []
        seen = set()
        for token in tokens:
            name = token.strip()
            if not name or name in seen:
                continue
            seen.add(name)
            alarms.append(name)
        return alarms

    def _match_profiles_for_alarm_names(alarm_names: list[str]) -> list[str]:
        alarm_set = set(alarm_names)
        matched_profiles = []
        for profile, names in arbel_alarm_catalog.items():
            if any(name in alarm_set for name in names):
                matched_profiles.append(profile)
        return matched_profiles

    arbel_choices = [
        questionary.Choice(f"{ICONS['rds']} RDS Monitoring", value="rds"),
        questionary.Choice("🖥️ EC2 Monitoring", value="ec2"),
        questionary.Choice(f"{ICONS['alarm']} Alarm Verification", value="alarm-name"),
        questionary.Choice(f"{ICONS['cost']} Daily Budget", value="budget"),
        questionary.Choice(f"{ICONS['backup']} Backup", value="backup"),
    ]

    region = "ap-southeast-3"
    step = "mode"
    choice = None
    selected_profiles = None
    alarm_source = "from-account"

    while True:
        if step == "mode":
            choice = common._select_prompt(
                f"{ICONS['arbel']} Aryanoble - Pilih Mode",
                arbel_choices,
                allow_back=True,
            )
            if choice is None:
                return None  # Escape at top level = exit flow

            if choice == "backup":
                run_group_specific(
                    "backup", all_profiles, region, group_name="Aryanoble"
                )
                return {"mode": "backup"}

            if choice == "alarm-name":
                step = "alarm_source"
            else:
                step = "accounts"

        elif step == "accounts":
            if choice == "alarm-name":
                alarm_profiles = list(arbel_alarm_catalog.keys())
                profile_choices = [
                    questionary.Choice(p, value=p, checked=False)
                    for p in alarm_profiles
                ]
            elif choice == "ec2":
                profile_choices = [
                    questionary.Choice(p, value=p, checked=True) for p in ec2_profiles
                ]
            else:
                profile_choices = [
                    questionary.Choice(p, value=p, checked=(p in default_rds_profiles))
                    for p in arbel_profiles
                ]

            selected_profiles = common._checkbox_prompt(
                f"{ICONS['check']} Pilih akun Aryanoble",
                profile_choices,
                allow_back=True,
            )
            if selected_profiles is None:
                # Escape = back to mode picker
                step = "mode"
                continue
            if not selected_profiles:
                print_error("Tidak ada akun dipilih.")
                continue  # Stay on accounts step

            if choice == "budget":
                profiles_for_budget = list(selected_profiles or [])
                run_group_specific(
                    "daily-budget",
                    profiles_for_budget,
                    region,
                    group_name="Aryanoble Budget",
                )
                return {"mode": "budget"}

            if choice == "alarm-name":
                step = (
                    "alarm_input" if alarm_source == "paste-input" else "alarm_select"
                )
            else:
                step = "window"

        elif step == "alarm_source":
            alarm_source = common._select_prompt(
                f"{ICONS['alarm']} Alarm Verification - Pilih Metode",
                [
                    questionary.Choice("By Account", value="from-account"),
                    questionary.Choice("By Alarm Names", value="paste-input"),
                ],
                default="from-account",
                allow_back=True,
            )
            if alarm_source is None:
                step = "mode"
                continue
            if alarm_source == "paste-input":
                step = "alarm_input"
            else:
                step = "accounts"

        elif step == "window":
            profiles_for_window = list(selected_profiles or [])
            window_choices = [
                questionary.Choice("1 Jam", value=(1, "1 Hour")),
                questionary.Choice("3 Jam", value=(3, "3 Hours")),
                questionary.Choice("12 Jam", value=(12, "12 Hours")),
            ]
            window_icon = "🖥️" if choice == "ec2" else ICONS["rds"]
            window_label = "EC2" if choice == "ec2" else "RDS"
            selected_window = common._select_prompt(
                f"{window_icon} Pilih Window {window_label}",
                window_choices,
                default=(3, "3 Hours"),
                allow_back=True,
            )
            if selected_window is None:
                # Escape = back to account picker
                step = "accounts"
                continue

            window_hours, suffix = selected_window
            run_group_specific(
                "daily-arbel",
                profiles_for_window,
                region,
                group_name=f"Aryanoble {window_label} ({suffix})",
                check_kwargs={
                    "window_hours": window_hours,
                    "section_scope": "ec2" if choice == "ec2" else "rds",
                },
            )
            return {"mode": choice}

        elif step == "alarm_select":
            profiles_for_alarm = list(selected_profiles or [])
            candidate_alarms = []
            seen = set()
            for profile in profiles_for_alarm:
                for alarm_name in arbel_alarm_catalog.get(profile, []):
                    if alarm_name not in seen:
                        seen.add(alarm_name)
                        candidate_alarms.append(alarm_name)

            if candidate_alarms:
                alarm_choices = [
                    questionary.Choice(a, value=a, checked=False)
                    for a in candidate_alarms
                ]
                selected_alarms = common._checkbox_prompt(
                    f"{ICONS['alarm']} Pilih alarm", alarm_choices, allow_back=True
                )
                if selected_alarms is None:
                    # Escape = back to account picker
                    step = "accounts"
                    continue
                if not selected_alarms:
                    print_error("Nama alarm wajib diisi.")
                    continue  # Stay on alarm_select
            else:
                alarm_input = common._text_prompt(
                    "Masukkan nama alarm (pisahkan dengan koma):",
                    allow_back=True,
                )
                if alarm_input is None:
                    step = "accounts"
                    continue
                selected_alarms = _parse_alarm_input(alarm_input or "")
                if not selected_alarms:
                    print_error("Nama alarm wajib diisi.")
                    continue

            run_group_specific(
                "alarm_verification",
                profiles_for_alarm,
                region,
                group_name="Aryanoble Alarm",
                check_kwargs={
                    "alarm_names": selected_alarms,
                    "min_duration_minutes": 10,
                },
            )
            return {"mode": "alarm"}

        elif step == "alarm_input":
            alarm_input = common._text_prompt(
                "Paste nama alarm (koma atau baris baru):",
                allow_back=True,
            )
            if alarm_input is None:
                step = "alarm_source"
                continue

            selected_alarms = _parse_alarm_input(alarm_input or "")
            if not selected_alarms:
                print_error("Nama alarm wajib diisi.")
                continue

            profiles_for_alarm = _match_profiles_for_alarm_names(selected_alarms)
            if not profiles_for_alarm:
                print_error(
                    "Alarm tidak ditemukan pada katalog account. Gunakan By Account atau update alarm_names di config."
                )
                continue

            run_group_specific(
                "alarm_verification",
                profiles_for_alarm,
                region,
                group_name="Aryanoble Alarm",
                check_kwargs={
                    "alarm_names": selected_alarms,
                    "min_duration_minutes": 10,
                },
            )
            return {"mode": "alarm"}


def _run_generic_customer(cfg):
    """Generic customer flow: run configured checks across all accounts.

    Checks that the consolidated report knows how to render (cost, guardduty,
    cloudwatch, notifications, backup, daily-arbel) are run together via
    run_all_checks() to produce a single DAILY MONITORING REPORT.

    Other checks (health, ec2list, etc.) are run individually via
    run_group_specific().
    """
    customer_id = cfg["customer_id"]
    display_name = cfg.get("display_name", customer_id)
    output_mode = "summary"
    checks = cfg.get("checks") or []
    accounts = cfg.get("accounts") or []

    if not checks:
        print_error(f"Tidak ada checks dikonfigurasi untuk {display_name}")
        return None

    valid_checks = [check for check in checks if check in AVAILABLE_CHECKS]
    if not valid_checks:
        print_error(f"Checks untuk {display_name} tidak valid atau belum terdaftar.")
        return None

    selected_checks = None
    selected_profiles = None
    step = "checks"
    while True:
        if step == "checks":
            _render_breadcrumb(f"Customer Report > {display_name} > Checks")
            check_choices = [
                questionary.Choice(check_name, value=check_name, checked=True)
                for check_name in valid_checks
            ]
            selected_checks = common._checkbox_prompt(
                f"{ICONS['check']} Pilih Checks untuk {display_name}",
                check_choices,
                allow_back=True,
            )
            if selected_checks is None:
                return {"back": True}
            if not selected_checks:
                print_error("Tidak ada check dipilih.")
                return None
            step = "accounts"

        elif step == "accounts":
            _render_breadcrumb(f"Customer Report > {display_name} > Accounts")
            account_choices = [
                questionary.Choice(
                    (a.get("display_name") or a.get("profile") or "Unknown"),
                    value=a["profile"],
                    checked=True,
                )
                for a in accounts
                if a.get("profile")
            ]
            selected_profiles = common._checkbox_prompt(
                f"{ICONS['check']} Pilih akun untuk {display_name}",
                account_choices,
                allow_back=True,
            )
            if selected_profiles is None:
                step = "checks"
                continue
            if not selected_profiles:
                print_error("Tidak ada akun dipilih.")
                continue
            break

    # Determine region from first selected account or default
    region = "ap-southeast-3"
    for a in accounts:
        if a["profile"] in selected_profiles and a.get("region"):
            region = a["region"]
            break

    selected_checks = list(selected_checks or [])
    selected_profiles = list(selected_profiles or [])

    # Split checks: consolidated (checker has render_section) vs individual
    consolidated = [
        c
        for c in selected_checks
        if c in AVAILABLE_CHECKS
        and AVAILABLE_CHECKS[c](region="").supports_consolidated
    ]
    individual = [c for c in selected_checks if c not in consolidated]

    # Run individual checks first (health, ec2list, etc.)
    for check_name in individual:
        check_kwargs = None
        if check_name == "alarm_verification":
            alarm_names = []
            for profile in selected_profiles:
                alarm_names.extend(get_alarm_names_for_profile(profile))

            deduped_alarm_names = []
            seen_alarm_names = set()
            for alarm_name in alarm_names:
                if alarm_name in seen_alarm_names:
                    continue
                seen_alarm_names.add(alarm_name)
                deduped_alarm_names.append(alarm_name)

            if not deduped_alarm_names:
                print_error(
                    "Alarm belum dikonfigurasi untuk akun yang dipilih. "
                    "Tambahkan alarm_names di configs/customers/<customer>.yaml"
                )
                continue

            check_kwargs = {
                "alarm_names": deduped_alarm_names,
                "min_duration_minutes": 10,
            }

        run_group_specific(
            check_name,
            selected_profiles,
            region,
            group_name=display_name,
            check_kwargs=check_kwargs,
        )

    # Run consolidated checks via run_all_checks for a unified daily report
    if consolidated:
        checks_override = {
            name: AVAILABLE_CHECKS[name]
            for name in consolidated
            if name in AVAILABLE_CHECKS
        }
        has_backup_rds = "backup" in checks_override or "daily-arbel" in checks_override
        profile_regions = _build_profile_regions(accounts, selected_profiles)
        check_kwargs_by_name = None
        if "aws-utilization-3core" in checks_override and profile_regions:
            check_kwargs_by_name = {
                "aws-utilization-3core": {"profile_regions": profile_regions}
            }
        run_all_checks(
            profiles=selected_profiles,
            region=region,
            group_name=display_name,
            checks_override=checks_override,
            check_kwargs_by_name=check_kwargs_by_name,
            exclude_backup_rds=not has_backup_rds,
            output_mode=output_mode,
        )

    return {"customer_id": customer_id, "checks": selected_checks}


def _prompt_slack(cfg):
    """Prompt operator to send report to customer's Slack."""
    slack_cfg = cfg.get("slack", {})
    display_name = cfg.get("display_name", cfg.get("customer_id", ""))

    if not slack_cfg.get("enabled"):
        console.print(
            f"[dim]Slack belum diaktifkan untuk {display_name}. "
            f"Set slack.enabled: true di configs/customers/{cfg.get('customer_id')}.yaml[/dim]"
        )
        return

    webhook_url = slack_cfg.get("webhook_url", "")
    if not webhook_url:
        console.print(
            f"[yellow]{ICONS['info']} Slack webhook_url belum dikonfigurasi untuk {display_name}[/yellow]"
        )
        return

    channel = slack_cfg.get("channel", "")
    channel_display = channel or "(default channel)"

    send = common._confirm_prompt(
        f"Kirim report ke Slack {display_name} ({channel_display})?",
        default=False,
        allow_back=True,
    )
    if send is None:
        return

    if not send:
        console.print("[dim]Slack send dilewati.[/dim]")
        return

    from src.integrations.slack.notifier import send_to_webhook

    sent, reason = send_to_webhook(
        webhook_url, f"Report for {display_name}", channel=channel or None
    )
    if sent:
        console.print(
            f"[green]{ICONS['check']} Report terkirim ke Slack {display_name} ({channel_display})[/green]"
        )
    else:
        console.print(f"[red]{ICONS['error']} Gagal kirim ke Slack: {reason}[/red]")


def _run_customer_auto(cfg):
    """Run a customer with all accounts and all configured checks — no prompts.

    Used by multi-customer mode to run each customer automatically.
    """
    customer_id = cfg["customer_id"]
    display_name = cfg.get("display_name", customer_id)
    output_mode = "summary"
    checks = cfg.get("checks") or []
    accounts = cfg.get("accounts") or []

    if not checks or not accounts:
        return

    valid_checks = [c for c in checks if c in AVAILABLE_CHECKS]
    if not valid_checks:
        return

    selected_profiles = [a["profile"] for a in accounts if a.get("profile")]
    if not selected_profiles:
        return

    region = "ap-southeast-3"
    for a in accounts:
        if a.get("profile") in selected_profiles and a.get("region"):
            region = a["region"]
            break

    consolidated = [
        c
        for c in valid_checks
        if c in AVAILABLE_CHECKS
        and AVAILABLE_CHECKS[c](region="").supports_consolidated
    ]
    individual = [c for c in valid_checks if c not in consolidated]

    for check_name in individual:
        run_group_specific(
            check_name,
            selected_profiles,
            region,
            group_name=display_name,
        )

    if consolidated:
        checks_override = {
            name: AVAILABLE_CHECKS[name]
            for name in consolidated
            if name in AVAILABLE_CHECKS
        }
        has_backup_rds = "backup" in checks_override or "daily-arbel" in checks_override
        profile_regions = _build_profile_regions(accounts, selected_profiles)
        check_kwargs_by_name = None
        if "aws-utilization-3core" in checks_override and profile_regions:
            check_kwargs_by_name = {
                "aws-utilization-3core": {"profile_regions": profile_regions}
            }
        run_all_checks(
            profiles=selected_profiles,
            region=region,
            group_name=display_name,
            checks_override=checks_override,
            check_kwargs_by_name=check_kwargs_by_name,
            exclude_backup_rds=not has_backup_rds,
            output_mode=output_mode,
        )


def run_customer_report():
    """Main Customer Report flow.

    Escape at customer picker returns to mode selector.
    """
    print_mini_banner()
    print_section_header("Daily Check", ICONS["star"])

    customers = list_customers()
    if not customers:
        print_error("Tidak ada customer config ditemukan di configs/customers/")
        print_info("Jalankan: monitoring-hub customer init <customer_id>")
        return False

    _render_customer_dashboard(customers)

    did_run = False

    while True:
        _render_breadcrumb("Customer Report > Pilih Customer")
        customer_choices = [
            questionary.Choice(
                f"{c['display_name']} ({c['account_count']} akun)",
                value=c["customer_id"],
                checked=False,
            )
            for c in customers
        ]

        selected_ids = common._checkbox_prompt(
            f"{ICONS['all']} Pilih Customer (bisa 1 atau lebih)",
            customer_choices,
            allow_back=True,
        )
        if selected_ids is None:
            return did_run
        if not selected_ids:
            print_error("Tidak ada customer dipilih.")
            continue

        if len(selected_ids) == 1:
            selected_id = selected_ids[0]
            try:
                cfg = load_customer_config(selected_id)
            except Exception as exc:
                print_error(f"Gagal load config: {exc}")
                continue

            display_name = cfg.get("display_name", selected_id)
            console.print(f"\n[bold cyan]{ICONS['star']} {display_name}[/bold cyan]")
            console.print(
                f"[dim]Accounts: {len(cfg.get('accounts', []))} | "
                f"Checks: {', '.join(cfg.get('checks', []))}[/dim]\n"
            )

            if selected_id == "aryanoble":
                result = _run_aryanoble_subflow(cfg)
            else:
                result = _run_generic_customer(cfg)

            if result == {"back": True}:
                continue

            if result:
                _prompt_slack(cfg)
                did_run = True
            return did_run

        for cid in selected_ids:
            try:
                cfg = load_customer_config(cid)
            except Exception as exc:
                print_error(f"Gagal load config {cid}: {exc}")
                continue
            display = cfg.get("display_name", cid)
            console.print(f"\n[bold cyan]{ICONS['star']} {display}[/bold cyan]")
            _run_customer_auto(cfg)
            did_run = True
        return did_run
