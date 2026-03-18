"""Settings menu interactive flow."""

import questionary
from rich import box
from rich.panel import Panel
from rich.table import Table

from src.app.tui import common
from src.core.runtime.config import PROFILE_GROUPS
from src.core.runtime.config_loader import get_config, create_sample_config, CONFIG_FILE
from src.core.runtime.ui import (
    VERSION,
    console,
    print_info,
    print_mini_banner,
    print_section_header,
    print_success,
    print_warning,
    ICONS,
)


def run_settings_menu(current_ui_mode, ui_modes):
    print_mini_banner()
    print_section_header("Settings & Info", ICONS["settings"])
    console.print(
        Panel(
            "Kelola config default region, workers, dan profile groups.\n"
            "Gunakan sample config untuk bootstrap environment baru.",
            title="⚙️ Configuration Center",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )
    console.print()

    config = get_config()

    info_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    info_table.add_column("Key", style="dim")
    info_table.add_column("Value")
    info_table.add_row("Version", VERSION)
    info_table.add_row("Config File", str(CONFIG_FILE))
    info_table.add_row(
        "Config Exists",
        "[green]Yes[/green]"
        if config.config_exists()
        else "[dim]No (using defaults)[/dim]",
    )
    info_table.add_row("Default Region", config.default_region)
    info_table.add_row("Parallel Workers", str(config.default_workers))
    info_table.add_row("Profile Groups", str(len(list(PROFILE_GROUPS.keys()))))
    info_table.add_row("UI Mode", ui_modes.get(current_ui_mode, current_ui_mode))
    console.print(info_table)
    console.print()

    settings_choices = [
        questionary.Choice(
            f"{ICONS['settings']} Create sample config", value="create_config"
        ),
        questionary.Choice(
            f"{ICONS['sparkle']} Toggle UI mode (Dense/Compact)", value="toggle_ui"
        ),
        questionary.Choice(f"{ICONS['info']} Show config path", value="show_path"),
        questionary.Choice(f"{ICONS['arrow']} Back to main menu", value="back"),
    ]
    choice = common._select_prompt(f"{ICONS['settings']} Settings", settings_choices)

    if choice == "create_config":
        if config.config_exists():
            print_warning(f"Config sudah ada di {CONFIG_FILE}")
        else:
            path = create_sample_config()
            print_success(f"Config sample dibuat di {path}")
            print_info("Edit file tersebut untuk menambah/mengubah profile groups.")
    elif choice == "toggle_ui":
        current_ui_mode = "compact" if current_ui_mode == "dense" else "dense"
        print_success(
            f"UI mode aktif: {ui_modes.get(current_ui_mode, current_ui_mode)}"
        )
    elif choice == "show_path":
        print_info(f"Config path: {CONFIG_FILE}")

    return current_ui_mode
