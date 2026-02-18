"""CloudWatch cost interactive flow."""

from datetime import datetime, timedelta

import boto3
import questionary
from botocore.exceptions import BotoCoreError, ClientError
from rich import box
from rich.panel import Panel

from src.app.tui import common
from src.checks import cloudwatch_cost_report as cw_cost_report
from src.core.runtime.config import CUSTOM_STYLE
from src.core.runtime.ui import (
    console,
    print_error,
    print_info,
    print_mini_banner,
    print_section_header,
    ICONS,
)


def _format_cw_plain(rows, names, start, end, region, top):
    rows_sorted = sorted(rows, key=lambda row: row["cost"], reverse=True)
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

    total_cost = sum(row["cost"] for row in rows)
    total_usage = sum(row["usage"] for row in rows)

    for idx, row in enumerate(rows_sorted, start=1):
        account = row["account"]
        name = (names.get(account, "") or "")[:38]
        cost = float(row["cost"])
        usage = float(row["usage"])
        lines.append(f"{idx:>2}  {account:<12} {name:<38} {cost:>9.2f} {usage:>12,.2f}")

    lines.append("-" * 80)
    lines.append(
        f"{'':>2}  {'':<12} {'TOTAL':<38} {float(total_cost):>9.2f} {float(total_usage):>12,.2f}"
    )
    return "\n".join(lines)


def run_cloudwatch_cost_report():
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
    region = common._choose_region([]) or "ap-southeast-3"

    format_choices = [
        questionary.Choice(f"{ICONS['dot']} Teams (plain text)", value="teams"),
        questionary.Choice(f"{ICONS['dot']} Markdown table", value="markdown"),
        questionary.Choice(f"{ICONS['dot']} Rich table (terminal)", value="table"),
    ]
    fmt_choice = common._select_prompt(
        f"{ICONS['settings']} Format Output", format_choices
    )
    if not fmt_choice:
        return

    try:
        top_str = questionary.text(
            "Top berapa akun?",
            default="10",
            style=CUSTOM_STYLE,
        ).ask()
    except KeyboardInterrupt:
        common._handle_interrupt(exit_direct=True)
        return

    try:
        top_n = int(top_str) if top_str else 10
    except ValueError:
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
        markdown = cw_cost_report.format_markdown(
            rows, names, start.isoformat(), end.isoformat(), region, top_n
        )
        console.print(markdown)
    else:
        text = _format_cw_plain(
            rows, names, start.isoformat(), end.isoformat(), region, top_n
        )
        console.print(
            Panel(text, title="[bold]Cost Report[/bold]", border_style="cyan")
        )
