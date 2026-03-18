"""Nabati analysis interactive flow."""

from datetime import datetime

import questionary
from rich import box
from rich.table import Table

from src.checks.nabati_analysis import run_nabati_analysis
from src.core.runtime.config import PROFILE_GROUPS, CUSTOM_STYLE
from src.core.runtime.ui import (
    console,
    print_info,
    print_mini_banner,
    print_section_header,
    ICONS,
)


def run_nabati_check():
    print_mini_banner()
    print_section_header("Nabati Analysis", ICONS["nabati"])

    now = datetime.now()
    current_month = now.strftime("%Y-%m")

    month_input = questionary.text(
        f"{ICONS['info']} Bulan analisis (YYYY-MM, default: {current_month}):",
        default=current_month,
        style=CUSTOM_STYLE,
    ).ask()

    if not month_input:
        return

    month = month_input.strip() or current_month
    profiles = list(PROFILE_GROUPS["NABATI-KSNI"].keys())

    print_info(f"Menganalisis {len(profiles)} akun Nabati untuk bulan {month}...")

    with console.status("[bold cyan]Mengumpulkan data CPU & Cost...", spinner="dots"):
        results = run_nabati_analysis(profiles, month)

    _display_nabati_results(results)


def _display_nabati_results(data):
    results = data["results"]
    month = data["month"]

    high_cpu = []
    low_cpu = []
    total_cost = 0.0

    for result in results:
        if "error" in result:
            continue

        total_cost += result.get("cost", 0.0)

        if result.get("no_instances"):
            low_cpu.append(result)
        elif result.get("max_cpu", 0) >= 80:
            high_cpu.append(result)
        else:
            low_cpu.append(result)

    console.print()
    console.print(f"[bold cyan]Instances with spikes ≥80% ({month})[/bold cyan]")

    if high_cpu:
        high_table = Table(box=box.ROUNDED, show_header=True)
        high_table.add_column("Account", style="cyan")
        high_table.add_column("Account ID", style="dim")
        high_table.add_column("Instance", style="yellow")
        high_table.add_column("Max CPU", style="red bold")
        high_table.add_column("Time", style="dim")

        for result in sorted(
            high_cpu, key=lambda item: item.get("max_cpu", 0), reverse=True
        ):
            high_table.add_row(
                result["account_name"],
                result["profile"].split("-")[0]
                if "-" in result["profile"]
                else result["profile"],
                result.get("max_cpu_instance", "N/A"),
                f"{result.get('max_cpu', 0):.1f}%",
                result.get("max_cpu_time", "N/A"),
            )

        console.print(high_table)
    else:
        console.print("[dim]None[/dim]")

    console.print()
    console.print(f"[bold cyan]Instances with no spikes ≥80% ({month})[/bold cyan]")

    if low_cpu:
        low_table = Table(box=box.ROUNDED, show_header=True)
        low_table.add_column("Account", style="cyan")
        low_table.add_column("Status", style="green")
        low_table.add_column("Max CPU", style="yellow")

        for result in sorted(low_cpu, key=lambda item: item["account_name"]):
            if result.get("no_instances"):
                status = "No instances running"
                cpu = "N/A"
            else:
                status = f"Instance {result.get('max_cpu_instance', 'N/A')}"
                cpu = f"{result.get('max_cpu', 0):.1f}%"

            low_table.add_row(result["account_name"], status, cpu)

        console.print(low_table)

    console.print()
    console.print(f"[bold cyan]Total Cost - {month}[/bold cyan]")

    cost_table = Table(box=box.ROUNDED, show_header=True)
    cost_table.add_column("Account", style="cyan")
    cost_table.add_column("Cost (USD)", style="green", justify="right")

    for result in sorted(results, key=lambda item: item.get("cost", 0), reverse=True):
        if "error" not in result:
            cost_table.add_row(
                result["account_name"],
                f"${result.get('cost', 0):,.2f}",
            )

    cost_table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]${total_cost:,.2f}[/bold]",
    )

    console.print(cost_table)
    console.print()
