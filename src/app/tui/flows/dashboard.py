"""Dashboard renderers used by interactive TUI menu."""

from rich import box
from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table

from src.core.runtime.ui import console, ICONS


def render_main_dashboard(is_dense_mode, current_ui_mode, ui_modes):
    if not is_dense_mode():
        quick = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        quick.add_column("k", style="dim")
        quick.add_column("v")
        quick.add_row("Core", "Single Check  |  All Checks  |  Arbel Check")
        quick.add_row("Support", "Cost Report  |  Settings")
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
        return

    ops = Panel(
        "[bold cyan]Single Check[/bold cyan]\nVerifikasi detail per akun\n\n"
        "[bold cyan]All Checks[/bold cyan]\nMonitoring paralel multi-akun\n\n"
        "[bold cyan]Arbel Check[/bold cyan]\nFlow RDS/Alarm/Backup",
        title="🛠️ Operations",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 2),
    )
    insight = Panel(
        "[bold magenta]Cost Report[/bold magenta]\nCloudWatch cost snapshot\n\n"
        "[bold magenta]Settings[/bold magenta]\nConfig, workers, UI mode",
        title="📊 Insights",
        border_style="magenta",
        box=box.ROUNDED,
        padding=(1, 2),
    )
    stats = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    stats.add_column("k", style="dim")
    stats.add_column("v")
    stats.add_row("UI Mode", ui_modes.get(current_ui_mode, current_ui_mode))
    stats.add_row("Focus", "Security + Ops + Cost")
    stats.add_row("Engine", "Parallel runner")
    console.print(
        Columns(
            [
                ops,
                insight,
                Panel(
                    stats,
                    title="📈 Status",
                    border_style="green",
                    box=box.ROUNDED,
                    padding=(1, 2),
                ),
            ],
            expand=True,
        )
    )
    console.print()


def render_single_check_dashboard(is_dense_mode):
    if not is_dense_mode():
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
        return

    security = Panel(
        f"{ICONS['health']} Health Events\n{ICONS['guardduty']} GuardDuty Findings\n{ICONS['cloudwatch']} CloudWatch Alarms",
        title="🔐 Security",
        border_style="red",
        box=box.ROUNDED,
        padding=(1, 2),
    )
    operations = Panel(
        f"{ICONS['backup']} Backup Status\n{ICONS['rds']} Daily Arbel\n{ICONS['alarm']} Alarm Verification",
        title="⚙️ Operations",
        border_style="green",
        box=box.ROUNDED,
        padding=(1, 2),
    )
    utility = Panel(
        f"{ICONS['cost']} Cost Anomalies\n{ICONS['notifications']} Notifications\n{ICONS['ec2list']} EC2 List",
        title="🧰 Utility",
        border_style="yellow",
        box=box.ROUNDED,
        padding=(1, 2),
    )
    console.print(Columns([security, operations, utility], expand=True))
    console.print()


def render_all_checks_dashboard(profile_count, is_dense_mode):
    if not is_dense_mode():
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
        return

    run_panel = Panel(
        f"Target accounts: [bold]{profile_count}[/bold]\nMode: Parallel checks\nOutput: Executive summary + detail",
        title="🚀 Run Plan",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 2),
    )
    focus_panel = Panel(
        "Cost anomalies\nGuardDuty\nCloudWatch\nNotifications",
        title="🎯 Focus Areas",
        border_style="magenta",
        box=box.ROUNDED,
        padding=(1, 2),
    )
    hint_panel = Panel(
        "Gunakan group profiles untuk coverage penuh\nGunakan region default jika tidak yakin",
        title="💡 Hint",
        border_style="bright_black",
        box=box.ROUNDED,
        padding=(1, 2),
    )
    console.print(Columns([run_panel, focus_panel, hint_panel], expand=True))
    console.print()
