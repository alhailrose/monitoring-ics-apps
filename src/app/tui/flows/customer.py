"""Customer Report interactive flow.

Pilih customer -> jalankan checks dari YAML -> Slack prompt.
Aryanoble punya sub-flow khusus (RDS/Alarm/Budget/Backup).
"""

import questionary
from rich import box
from rich.panel import Panel
from rich.table import Table

from src.app.tui import common
from src.configs.loader import list_customers, load_customer_config
from src.core.runtime.config import AVAILABLE_CHECKS, CUSTOM_STYLE
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
    table.add_column("Checks", style="white")
    table.add_column("Slack", style="white")

    for c in customers:
        slack_status = "[green]ON[/green]" if c.get("slack_enabled") else "[dim]off[/dim]"
        checks_str = ", ".join(c.get("checks", [])[:3])
        if len(c.get("checks", [])) > 3:
            checks_str += f" +{len(c['checks']) - 3}"
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


def _run_aryanoble_subflow(cfg):
    """Aryanoble-specific sub-flow: RDS Monitoring / Alarm Verification / Budget / Backup."""
    arbel_profiles = [
        a["profile"] for a in cfg.get("accounts", [])
        if a.get("daily_arbel")
    ]
    all_profiles = [a["profile"] for a in cfg.get("accounts", [])]
    default_rds_profiles = ["dermies-max", "cis-erha", "connect-prod"]

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
        "public-web": [
            "CPU Utilization RDS (Mysql)",
            "CPU Utilization RDS (Postgre)",
            "FreeableMemory RDS (Mysql)",
            "FreeableMemory RDS (Postgre)",
            "Total Connection RDS (Mysql)",
            "Total Connection RDS (Postgre)",
        ],
        "fee-doctor": [
            "feedoctor-production-rds-cpu-above-70",
            "feedoctor-production-rds-mem < 2GB",
            "feedoctor-production-backend-cpu-above-70",
            "feedoctor-production-backend-disk-above-70",
            "feedoctor-production-backend-mem-above-70",
            "feedoctor-production-frontend-cpu-above-70",
            "feedoctor-production-frontend-disk-above-70",
            "feedoctor-production-frontend-mem-above-70",
        ],
        "iris-prod": [
            "rnd-formulation-production-rds-cpu-above-70",
            "rnd-formulation-production-appserver-cpu-above-70",
            "rnd-formulation-production-appserver-disk-above-70",
            "rnd-formulation-production-appserver-mem-above-70",
        ],
        "iris-dev": [
            "rnd-formulation-dev-appserver-cpu-above-70",
            "rnd-formulation-dev-appserver-disk-above-70",
            "rnd-formulation-dev-appserver-mem-above-70",
            "rnd-formulation-dev-database-cpu-above-70",
            "rnd-formulation-dev-database-disk-above-70",
            "rnd-formulation-dev-database-mem-above-70",
        ],
        "HRIS": [
            "aryanoble-prod-Window2019Base-webserver-cpu-above-80",
            "aryanoble-prod-Window2019Base-webserver-mem-above-80",
            "aryanoble-prod-Windows2019+SQL2019Standard-database-cpu-above-80",
            "aryanoble-prod-Windows2019+SQL2019Standard-database-mem-above-80",
            "aryanoble-prod-Ubuntu20.04-openvpn-cpu-above-80",
            "aryanoble-prod-Ubuntu20.04-openvpn-mem-above-80",
            "aryanoble-prod-Ubuntu20.04-openvpn-disk-above-80",
        ],
        "sfa": [
            "vm-sfa-cpu-above-70",
            "vm-sfa-disk-above-70",
            "vm-sfa-mem-above-70",
            "vm-database-cpu-above-70",
            "vm-database-mem-above-70",
            "vm-jobs-cpu-above-70",
            "vm-jobs-disk-above-70",
            "vm-jobs-mem-above-70",
            "vm-dms-cpu-above-70",
            "vm-dms-mem-above-70",
        ],
        "dwh": [
            "dc-dwh-db-cpu-above-70",
            "dc-dwh-db-memory-above-70",
            "dc-dwh-olap-cpu-above-70",
            "dc-dwh-olap-memory-above-70",
        ],
        "tgw": [
            "VPN Tunnel State",
            "Second VPN Tunnel State",
        ],
        "backup-hris": [
            "Disk C Free Space is Below 20%",
            "Disk D Free Space Below 20%",
            "Disk E Free Space Below 20%",
            "Disk F Free Space Below 20%",
            "Disk G Free Space Below 20%",
        ],
    }

    arbel_choices = [
        questionary.Choice(f"{ICONS['rds']} RDS Monitoring", value="rds"),
        questionary.Choice(f"{ICONS['alarm']} Alarm Verification", value="alarm-name"),
        questionary.Choice(f"{ICONS['cost']} Daily Budget", value="budget"),
        questionary.Choice(f"{ICONS['backup']} Backup", value="backup"),
    ]

    choice = common._select_prompt(
        f"{ICONS['arbel']} Aryanoble - Pilih Mode", arbel_choices
    )
    if not choice:
        return None

    region = "ap-southeast-3"

    if choice == "backup":
        run_group_specific("backup", all_profiles, region, group_name="Aryanoble")
        return {"mode": "backup"}

    # Pick profiles based on mode
    if choice == "alarm-name":
        # Alarm verification: show all accounts that have alarm catalog entries
        alarm_profiles = list(arbel_alarm_catalog.keys())
        profile_choices = [
            questionary.Choice(p, value=p, checked=True)
            for p in alarm_profiles
        ]
    else:
        # RDS/Budget: show accounts with daily_arbel config
        profile_choices = [
            questionary.Choice(
                p, value=p, checked=(p in default_rds_profiles)
            )
            for p in arbel_profiles
        ]

    selected_profiles = common._checkbox_prompt(
        f"{ICONS['check']} Pilih akun Aryanoble", profile_choices
    )
    if not selected_profiles:
        print_error("Tidak ada akun dipilih.")
        return None

    if choice == "budget":
        run_group_specific(
            "daily-budget",
            selected_profiles,
            region,
            group_name="Aryanoble Budget",
        )
        return {"mode": "budget"}

    if choice == "alarm-name":
        candidate_alarms = []
        seen = set()
        for profile in selected_profiles:
            for alarm_name in arbel_alarm_catalog.get(profile, []):
                if alarm_name not in seen:
                    seen.add(alarm_name)
                    candidate_alarms.append(alarm_name)

        if candidate_alarms:
            alarm_choices = [
                questionary.Choice(a, value=a, checked=True)
                for a in candidate_alarms
            ]
            selected_alarms = common._checkbox_prompt(
                f"{ICONS['alarm']} Pilih alarm", alarm_choices
            )
            if not selected_alarms:
                print_error("Nama alarm wajib diisi.")
                return None
        else:
            try:
                alarm_input = questionary.text(
                    "Masukkan nama alarm (pisahkan dengan koma):",
                    style=CUSTOM_STYLE,
                ).ask()
            except KeyboardInterrupt:
                common._handle_interrupt(exit_direct=True)
                return None
            selected_alarms = [x.strip() for x in (alarm_input or "").split(",") if x.strip()]
            if not selected_alarms:
                print_error("Nama alarm wajib diisi.")
                return None

        run_group_specific(
            "alarm_verification",
            selected_profiles,
            region,
            group_name="Aryanoble Alarm",
            check_kwargs={
                "alarm_names": selected_alarms,
                "min_duration_minutes": 10,
            },
        )
        return {"mode": "alarm"}

    # RDS Monitoring
    window_choices = [
        questionary.Choice("1 Jam", value=(1, "1 Hour")),
        questionary.Choice("3 Jam", value=(3, "3 Hours")),
        questionary.Choice("12 Jam", value=(12, "12 Hours")),
    ]
    selected_window = common._select_prompt(
        f"{ICONS['rds']} Pilih Window RDS", window_choices, default=(3, "3 Hours")
    )
    if not selected_window:
        return None

    window_hours, suffix = selected_window
    run_group_specific(
        "daily-arbel",
        selected_profiles,
        region,
        group_name=f"Aryanoble ({suffix})",
        check_kwargs={"window_hours": window_hours},
    )
    return {"mode": "rds"}


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
    checks = cfg.get("checks", [])
    accounts = cfg.get("accounts", [])

    if not checks:
        print_error(f"Tidak ada checks dikonfigurasi untuk {display_name}")
        return None

    # Let operator select/deselect checks
    check_choices = [
        questionary.Choice(c, value=c, checked=True)
        for c in checks
        if c in AVAILABLE_CHECKS
    ]
    if not check_choices:
        print_error(f"Tidak ada checks valid untuk {display_name}")
        return None

    selected_checks = common._checkbox_prompt(
        f"{ICONS['check']} Checks untuk {display_name}", check_choices
    )
    if not selected_checks:
        print_error("Tidak ada check dipilih.")
        return None

    # Let operator select/deselect accounts
    account_choices = [
        questionary.Choice(
            f"{a.get('display_name', a['profile'])} ({a.get('account_id', 'N/A')})",
            value=a["profile"],
            checked=True,
        )
        for a in accounts
    ]

    selected_profiles = common._checkbox_prompt(
        f"{ICONS['check']} Akun untuk {display_name}", account_choices
    )
    if not selected_profiles:
        print_error("Tidak ada akun dipilih.")
        return None

    # Determine region from first selected account or default
    region = "ap-southeast-3"
    for a in accounts:
        if a["profile"] in selected_profiles and a.get("region"):
            region = a["region"]
            break

    # Split checks: consolidated (checker has render_section) vs individual
    consolidated = [
        c for c in selected_checks
        if c in AVAILABLE_CHECKS and AVAILABLE_CHECKS[c](region="").supports_consolidated
    ]
    individual = [c for c in selected_checks if c not in consolidated]

    # Run individual checks first (health, ec2list, etc.)
    for check_name in individual:
        run_group_specific(
            check_name,
            selected_profiles,
            region,
            group_name=display_name,
        )

    # Run consolidated checks via run_all_checks for a unified daily report
    if consolidated:
        checks_override = {
            name: AVAILABLE_CHECKS[name]
            for name in consolidated
            if name in AVAILABLE_CHECKS
        }
        has_backup_rds = "backup" in checks_override or "daily-arbel" in checks_override
        run_all_checks(
            profiles=selected_profiles,
            region=region,
            group_name=display_name,
            checks_override=checks_override,
            exclude_backup_rds=not has_backup_rds,
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

    try:
        send = questionary.confirm(
            f"Kirim report ke Slack {display_name} ({channel_display})?",
            default=False,
            style=CUSTOM_STYLE,
        ).ask()
    except KeyboardInterrupt:
        return

    if not send:
        console.print("[dim]Slack send dilewati.[/dim]")
        return

    from src.integrations.slack.notifier import send_to_webhook

    sent, reason = send_to_webhook(webhook_url, f"Report for {display_name}", channel=channel or None)
    if sent:
        console.print(
            f"[green]{ICONS['check']} Report terkirim ke Slack {display_name} ({channel_display})[/green]"
        )
    else:
        console.print(
            f"[red]{ICONS['error']} Gagal kirim ke Slack: {reason}[/red]"
        )


def run_customer_report():
    """Main Customer Report flow."""
    print_mini_banner()
    print_section_header("Customer Report", ICONS["star"])

    customers = list_customers()
    if not customers:
        print_error("Tidak ada customer config ditemukan di configs/customers/")
        print_info("Jalankan: monitoring-hub customer init <customer_id>")
        return

    _render_customer_dashboard(customers)

    # Pick customer
    customer_choices = [
        questionary.Choice(
            f"{c['display_name']} ({c['account_count']} akun)",
            value=c["customer_id"],
        )
        for c in customers
    ]

    selected_id = common._select_prompt(
        f"{ICONS['star']} Pilih Customer", customer_choices
    )
    if not selected_id:
        return

    try:
        cfg = load_customer_config(selected_id)
    except Exception as exc:
        print_error(f"Gagal load config: {exc}")
        return

    display_name = cfg.get("display_name", selected_id)
    console.print(f"\n[bold cyan]{ICONS['star']} {display_name}[/bold cyan]")
    console.print(
        f"[dim]Accounts: {len(cfg.get('accounts', []))} | "
        f"Checks: {', '.join(cfg.get('checks', []))}[/dim]\n"
    )

    # Route to Aryanoble sub-flow or generic flow
    if selected_id == "aryanoble":
        result = _run_aryanoble_subflow(cfg)
    else:
        result = _run_generic_customer(cfg)

    if result:
        _prompt_slack(cfg)
