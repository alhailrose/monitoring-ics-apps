"""
Beautiful UI components for AWS Monitoring Hub.
ASCII art banner, status badges, progress indicators, and table formatters.
"""

from datetime import datetime
from typing import Optional
import importlib.metadata

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)
from rich.style import Style
from rich.box import ROUNDED, HEAVY, DOUBLE
from rich import box

# Version info
try:
    VERSION = importlib.metadata.version("monitoring-hub")
except importlib.metadata.PackageNotFoundError:
    VERSION = "0.0.0.dev"

# Console instance
console = Console()

# ASCII Art Banner
ASCII_BANNER = r"""
    ╔═╗╦ ╦╔═╗  ╔╦╗┌─┐┌┐┌┬┌┬┐┌─┐┬─┐┬┌┐┌┌─┐
    ╠═╣║║║╚═╗  ║║║│ │││││ │ │ │├┬┘│││││ ┬
    ╩ ╩╚╩╝╚═╝  ╩ ╩└─┘┘└┘┴ ┴ └─┘┴└─┴┘└┘└─┘
                      Hub
"""

ASCII_BANNER_MINI = r"""
   ▄▀█ █░█░█ █▀   █▀▄▀█ █▀█ █▄░█ █ ▀█▀ █▀█ █▀█
   █▀█ ▀▄▀▄▀ ▄█   █░▀░█ █▄█ █░▀█ █ ░█░ █▄█ █▀▄
"""

# Icons for menus (using Unicode symbols that work in most terminals)
ICONS = {
    "single": "🔍",
    "all": "📋",
    "arbel": "🏥",
    "nabati": "🍪",
    "cost": "💰",
    "health": "❤️",
    "guardduty": "🛡️",
    "cloudwatch": "📊",
    "backup": "💾",
    "rds": "🗄️",
    "notifications": "🔔",
    "alarm": "⏱️",
    "ec2list": "🖥️",
    "settings": "⚙️",
    "exit": "🚪",
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "pending": "⏳",
    "skip": "⊘",
    "arrow": "→",
    "check": "✓",
    "cross": "✗",
    "dot": "•",
    "star": "★",
    "sparkle": "✨",
}


# Status badges with colors
class StatusBadge:
    """Create colored status badges."""

    @staticmethod
    def ok(text: str = "OK") -> Text:
        return Text(f" ✓ {text} ", style="bold white on green")

    @staticmethod
    def warn(text: str = "WARN") -> Text:
        return Text(f" ⚠ {text} ", style="bold black on yellow")

    @staticmethod
    def error(text: str = "ERROR") -> Text:
        return Text(f" ✗ {text} ", style="bold white on red")

    @staticmethod
    def info(text: str = "INFO") -> Text:
        return Text(f" ℹ {text} ", style="bold white on blue")

    @staticmethod
    def skip(text: str = "SKIP") -> Text:
        return Text(f" ○ {text} ", style="bold white on bright_black")

    @staticmethod
    def pending(text: str = "PENDING") -> Text:
        return Text(f" ⏳ {text} ", style="bold black on cyan")

    @staticmethod
    def from_status(status: str) -> Text:
        """Create badge from status string."""
        status_lower = status.lower()
        if status_lower in ["ok", "clear", "normal", "completed", "success"]:
            return StatusBadge.ok(status.upper())
        elif status_lower in ["warn", "warning", "attention", "attention required"]:
            return StatusBadge.warn("WARN")
        elif status_lower in ["error", "failed", "failure"]:
            return StatusBadge.error("ERROR")
        elif status_lower in ["skip", "skipped", "disabled"]:
            return StatusBadge.skip(status.upper())
        elif status_lower in ["pending", "running", "checking"]:
            return StatusBadge.pending(status.upper())
        else:
            return StatusBadge.info(status.upper())


# Color scheme
class Colors:
    """Consistent color scheme for the app."""

    PRIMARY = "cyan"
    SECONDARY = "green"
    ACCENT = "magenta"
    SUCCESS = "green"
    WARNING = "yellow"
    ERROR = "red"
    MUTED = "bright_black"
    HIGHLIGHT = "bold cyan"


def print_banner(show_version: bool = True, show_tips: bool = True):
    """Print the beautiful ASCII art banner."""
    now = datetime.now()

    # Greeting based on time
    hour = now.hour
    if 5 <= hour < 12:
        greeting = "Selamat Pagi"
        greeting_icon = "🌅"
    elif 12 <= hour < 17:
        greeting = "Selamat Siang"
        greeting_icon = "☀️"
    elif 17 <= hour < 21:
        greeting = "Selamat Sore"
        greeting_icon = "🌆"
    else:
        greeting = "Selamat Malam"
        greeting_icon = "🌙"

    banner_lines = [
        f"[bold cyan]{ASCII_BANNER}[/bold cyan]",
        f"[dim]Centralized AWS Security & Operations Monitoring[/dim]",
        "",
        f"{greeting_icon} [bold]{greeting}![/bold] [dim]•[/dim] [cyan]{now:%A, %d %B %Y}[/cyan] [dim]•[/dim] [green]{now:%H:%M} WIB[/green]",
    ]

    if show_version:
        banner_lines.append(f"[dim]Version {VERSION}[/dim]")

    console.print(
        Panel(
            "\n".join(banner_lines),
            border_style="cyan",
            box=box.ROUNDED,
            padding=(0, 2),
        )
    )

    if show_tips:
        # Keyboard shortcuts
        shortcuts = Text()
        shortcuts.append("  ⌨️  ", style="dim")
        shortcuts.append("Esc", style="bold cyan")
        shortcuts.append("/", style="dim")
        shortcuts.append("Ctrl+C", style="bold cyan")
        shortcuts.append(": kembali   ", style="dim")
        shortcuts.append("•", style="dim")
        shortcuts.append("   ", style="dim")
        shortcuts.append("Space", style="bold cyan")
        shortcuts.append(": pilih   ", style="dim")
        shortcuts.append("•", style="dim")
        shortcuts.append("   ", style="dim")
        shortcuts.append("Enter", style="bold cyan")
        shortcuts.append(": konfirmasi", style="dim")
        console.print(shortcuts)
    console.print()


def print_mini_banner():
    """Print a smaller banner for sub-screens."""
    console.print(f"[bold cyan]AWS Monitoring Hub[/bold cyan] [dim]v{VERSION}[/dim]")
    console.print()


def create_menu_choices():
    """Create beautified menu choices with icons."""
    return [
        {
            "value": "single",
            "title": f"{ICONS['single']} Single Check",
            "description": "Cek satu profil dengan detail lengkap",
        },
        {
            "value": "all",
            "title": f"{ICONS['all']} All Checks",
            "description": "Ringkasan multi-profil (parallel)",
        },
        {
            "value": "arbel",
            "title": f"{ICONS['arbel']} Arbel Check (mandatory)",
            "description": "Backup & RDS untuk AryaNoble",
        },
        {
            "value": "nabati",
            "title": f"{ICONS['nabati']} Nabati Analysis",
            "description": "CPU Usage & Cost untuk NABATI-KSNI",
        },
        {
            "value": "cw_cost",
            "title": f"{ICONS['cost']} Cost Report",
            "description": "CloudWatch cost & usage Jakarta",
        },
        {
            "value": "settings",
            "title": f"{ICONS['settings']} Settings",
            "description": "Konfigurasi & info",
        },
    ]


def create_check_choices():
    """Create beautified check type choices with icons."""
    return {
        "health": f"{ICONS['health']} Health Events",
        "cost": f"{ICONS['cost']} Cost Anomalies",
        "guardduty": f"{ICONS['guardduty']} GuardDuty",
        "cloudwatch": f"{ICONS['cloudwatch']} CloudWatch Alarms",
        "notifications": f"{ICONS['notifications']} Notifications",
        "backup": f"{ICONS['backup']} Backup Status",
        "daily-arbel": f"{ICONS['rds']} Daily Arbel",
        "ec2list": f"{ICONS['ec2list']} EC2 List",
    }


def create_progress_context(description: str = "Processing..."):
    """Create a rich progress context for long operations."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        TextColumn("[dim]{task.fields[status]}[/dim]"),
        console=console,
        transient=True,
    )


def create_summary_table(title: str, profiles: list, results: dict) -> Table:
    """Create a beautiful summary table for check results."""
    table = Table(
        title=f"[bold]{title}[/bold]",
        box=box.ROUNDED,
        border_style="cyan",
        header_style="bold cyan",
        show_header=True,
        padding=(0, 1),
    )

    # Add columns
    table.add_column("Profile", style="bold", min_width=20)
    table.add_column("Cost", justify="center", min_width=8)
    table.add_column("Guard", justify="center", min_width=8)
    table.add_column("CW", justify="center", min_width=8)
    table.add_column("Backup", justify="center", min_width=8)
    table.add_column("Daily Arbel", justify="center", min_width=8)

    def get_status_icon(check_results: dict) -> str:
        if not check_results:
            return "[dim]─[/dim]"
        status = check_results.get("status", "")
        if status == "error":
            return "[red]✗[/red]"
        elif status in ["disabled", "skipped"]:
            return "[dim]○[/dim]"
        elif check_results.get("total_anomalies", 0) > 0:
            return "[yellow]⚠[/yellow]"
        elif check_results.get("findings", 0) > 0:
            return "[yellow]⚠[/yellow]"
        elif check_results.get("count", 0) > 0:
            return "[yellow]⚠[/yellow]"
        elif check_results.get("issues", []):
            return "[yellow]⚠[/yellow]"
        else:
            return "[green]✓[/green]"

    for profile in profiles:
        profile_results = results.get(profile, {})
        table.add_row(
            profile,
            get_status_icon(profile_results.get("cost", {})),
            get_status_icon(profile_results.get("guardduty", {})),
            get_status_icon(profile_results.get("cloudwatch", {})),
            get_status_icon(profile_results.get("backup", {})),
            get_status_icon(profile_results.get("daily-arbel", {})),
        )

    return table


def print_check_header(check_name: str, profile: str, account_id: str, region: str):
    """Print a beautiful header for individual checks."""
    icon = ICONS.get(check_name, ICONS["info"])

    header_content = Text()
    header_content.append(f"{icon} ", style="bold")
    header_content.append(check_name.upper(), style="bold cyan")
    header_content.append("\n\n", style="")
    header_content.append("Profile  ", style="dim")
    header_content.append(profile, style="bold white")
    header_content.append("\n", style="")
    header_content.append("Account  ", style="dim")
    header_content.append(account_id, style="bold yellow")
    header_content.append("\n", style="")
    header_content.append("Region   ", style="dim")
    header_content.append(region, style="bold green")

    console.print(
        Panel(
            header_content,
            border_style="cyan",
            box=box.ROUNDED,
            title="[bold]Single Check[/bold]",
            title_align="left",
            padding=(1, 2),
        )
    )


def print_group_header(
    check_name: str, profile_count: int, group_name: Optional[str], region: str
):
    """Print a beautiful header for group checks."""
    icon = ICONS.get(check_name, ICONS["info"])

    header_content = Text()
    header_content.append(f"{icon} ", style="bold")
    header_content.append(check_name.upper(), style="bold cyan")
    header_content.append("\n\n", style="")
    header_content.append("Profiles  ", style="dim")
    header_content.append(str(profile_count), style="bold white")
    header_content.append(" accounts", style="dim")
    header_content.append("\n", style="")
    header_content.append("Group     ", style="dim")
    header_content.append(group_name or "-", style="bold yellow")
    header_content.append("\n", style="")
    header_content.append("Region    ", style="dim")
    header_content.append(region, style="bold green")

    console.print(
        Panel(
            header_content,
            border_style="cyan",
            box=box.ROUNDED,
            title="[bold]Multi-Account Check[/bold]",
            title_align="left",
            padding=(1, 2),
        )
    )


def print_result_row(profile: str, status: str, detail: str = ""):
    """Print a single result row with status badge."""
    badge = StatusBadge.from_status(status)

    output = Text()
    output.append("  ")
    output.append_text(badge)
    output.append("  ")
    output.append(profile, style="bold")
    if detail:
        output.append(f"  [dim]{detail}[/dim]")

    console.print(output)


def print_section_header(title: str, icon: str = ""):
    """Print a section header."""
    if icon:
        console.print(f"\n[bold cyan]{icon} {title}[/bold cyan]")
    else:
        console.print(f"\n[bold cyan]{title}[/bold cyan]")
    console.print("[dim]" + "─" * 50 + "[/dim]")


def print_tips():
    """Print random tips for users."""
    tips = [
        f"{ICONS['info']} Gunakan Group (SSO) agar daftar akun otomatis terisi.",
        f"{ICONS['info']} Backup dan RDS mendukung multi akun untuk laporan WhatsApp.",
        f"{ICONS['info']} Tekan Ctrl+C dua kali cepat untuk keluar.",
        f"{ICONS['info']} Single check cocok untuk verifikasi cepat per profil.",
        f"{ICONS['info']} Config eksternal di ~/.monitoring-hub/config.yaml",
    ]
    idx = datetime.now().minute % len(tips)
    console.print(f"\n[dim]{tips[idx]}[/dim]")


def print_success(message: str):
    """Print a success message."""
    console.print(f"[green]{ICONS['success']} {message}[/green]")


def print_error(message: str):
    """Print an error message."""
    console.print(f"[red]{ICONS['error']} {message}[/red]")


def print_warning(message: str):
    """Print a warning message."""
    console.print(f"[yellow]{ICONS['warning']} {message}[/yellow]")


def print_info(message: str):
    """Print an info message."""
    console.print(f"[cyan]{ICONS['info']} {message}[/cyan]")
