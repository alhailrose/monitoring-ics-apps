"""Shared helper utilities for TUI flows."""

import sys
from time import monotonic
from typing import Iterable

import questionary
from prompt_toolkit.key_binding import KeyBindings, merge_key_bindings
from prompt_toolkit.keys import Keys

from src.core.runtime.config import (
    PROFILE_GROUPS,
    INTERRUPT_EXIT_WINDOW,
    CUSTOM_STYLE,
    get_last_interrupt_ts,
    set_last_interrupt_ts,
)
from src.core.runtime.ui import console, print_error, ICONS
from src.core.runtime.utils import list_local_profiles, resolve_region


def _make_escape_bindings() -> KeyBindings:
    """Create a KeyBindings object that maps Escape → KeyboardInterrupt.

    Used to inject into questionary prompts so Escape alone (without Enter)
    immediately triggers back navigation.
    """
    kb = KeyBindings()

    @kb.add(Keys.Escape, eager=True)
    def _(event):
        event.app.exit(exception=KeyboardInterrupt, style="class:aborting")

    return kb


def _inject_escape_binding(question) -> None:
    """Inject an Escape key binding into a questionary Question's Application.

    Merges our escape binding with the existing key_bindings on the Application
    so Escape triggers KeyboardInterrupt immediately (no Enter needed).

    Silently skips if the question object has no .application attribute
    (e.g., in tests where questionary is monkeypatched with a fake object).
    """
    app = getattr(question, "application", None)
    if app is None:
        return
    existing = app.key_bindings
    escape_kb = _make_escape_bindings()
    if existing is not None:
        app.key_bindings = merge_key_bindings([existing, escape_kb])
    else:
        app.key_bindings = escape_kb


def _handle_interrupt(context="Kembali ke menu utama", exit_direct=False):
    """Handle Ctrl+C/Esc; in menus we exit immediately for convenience."""
    now = monotonic()
    if exit_direct:
        console.print(
            f"\n[bold green]{ICONS['exit']} Keluar dari AWS Monitoring Hub. Sampai jumpa![/bold green]\n"
        )
        sys.exit(0)

    last_ts = get_last_interrupt_ts()
    if now - last_ts <= INTERRUPT_EXIT_WINDOW:
        console.print(
            f"\n[bold green]{ICONS['exit']} Keluar dari AWS Monitoring Hub. Sampai jumpa![/bold green]\n"
        )
        sys.exit(0)

    set_last_interrupt_ts(now)
    console.print(
        f"\n[bold yellow]{ICONS['warning']} {context}[/bold yellow]. Tekan Ctrl+C lagi untuk keluar.\n"
    )


def _select_prompt(prompt, choices, default=None, allow_back: bool = False):
    """Beautiful select prompt with icons.

    Args:
        allow_back: If True, Ctrl+C/Escape returns None instead of sys.exit.
                    Use this inside sub-flows where user should be able to go back.
                    When allow_back=True, an Escape key binding is injected so
                    pressing Escape alone (without Enter) immediately triggers back.
    """
    try:
        instruction = (
            "(↑↓ navigasi, Enter pilih, Ctrl+C/Esc kembali)"
            if allow_back
            else "(Gunakan ↑↓ untuk navigasi, Enter untuk pilih)"
        )
        q = questionary.select(
            prompt,
            choices=choices,
            default=default
            if default in [c if isinstance(c, str) else c.value for c in choices]
            else None,
            style=CUSTOM_STYLE,
            instruction=instruction,
        )
        if allow_back:
            _inject_escape_binding(q)
        ans = q.ask()
    except KeyboardInterrupt:
        if allow_back:
            return None
        _handle_interrupt(exit_direct=True)
        return None
    return ans or None


def _checkbox_prompt(prompt, choices, allow_back: bool = False):
    """Beautiful checkbox prompt.

    Args:
        allow_back: If True, Ctrl+C/Escape returns None instead of sys.exit.
                    An Escape key binding is injected when allow_back=True so
                    pressing Escape alone immediately triggers back.
    """
    try:
        instruction = (
            "(Spasi pilih, Enter konfirmasi, Ctrl+C/Esc kembali)"
            if allow_back
            else "(Spasi untuk pilih, Enter untuk konfirmasi)"
        )
        q = questionary.checkbox(
            prompt,
            choices=choices,
            style=CUSTOM_STYLE,
            instruction=instruction,
        )
        if allow_back:
            _inject_escape_binding(q)
        ans = q.ask()
    except KeyboardInterrupt:
        if allow_back:
            return None
        _handle_interrupt(exit_direct=True)
        return None
    return ans or None


def filter_values_by_query(values: Iterable[str], query: str | None):
    """Return values that contain query (case-insensitive)."""
    all_values = list(values)
    normalized_query = (query or "").strip().lower()
    if not normalized_query:
        return all_values

    return [value for value in all_values if normalized_query in value.lower()]


def apply_bulk_action(
    values: Iterable[str], action: str, selected_values: Iterable[str] | None = None
):
    """Apply a bulk selection action to values."""
    all_values = list(values)
    if action == "select_all":
        return all_values
    if action == "clear_all":
        return []
    if action == "manual":
        return list(selected_values or [])

    raise ValueError(f"Unsupported bulk action: {action}")


def _searchable_multi_select_prompt(prompt, choices, ask_search=True):
    """Prompt user for optional search + bulk action + manual multi-select."""
    available_choices = list(choices)

    if ask_search:
        try:
            search_query = questionary.text(
                "Kata kunci pencarian (opsional):",
                style=CUSTOM_STYLE,
                default="",
            ).ask()
        except KeyboardInterrupt:
            _handle_interrupt(exit_direct=True)
            return []
        available_choices = filter_values_by_query(available_choices, search_query)

    if not available_choices:
        return []

    action_choices = [
        questionary.Choice("Pilih manual", value="manual"),
        questionary.Choice("Pilih semua", value="select_all"),
        questionary.Choice("Bersihkan semua", value="clear_all"),
    ]
    action = _select_prompt("Aksi pemilihan", action_choices, default="manual")
    if not action:
        return []

    if action in {"select_all", "clear_all"}:
        return apply_bulk_action(available_choices, action)

    selected_values = _checkbox_prompt(prompt, available_choices)
    return apply_bulk_action(available_choices, "manual", selected_values)


def _simple_account_select(display_name, accounts):
    """Simplified account selection with default select-all.
    
    Args:
        display_name: Customer display name
        accounts: List of account dicts with 'profile' key
        
    Returns:
        List of selected profile names
    """
    if not accounts:
        return []
    
    # Show info
    console.print(
        f"\n[cyan]{display_name}[/cyan] memiliki [yellow]{len(accounts)}[/yellow] akun aktif"
    )
    
    # Ask: use all accounts?
    try:
        use_all = questionary.confirm(
            f"{ICONS['check']} Pilih semua akun?",
            default=True,  # Default YES
            style=CUSTOM_STYLE,
        ).ask()
    except KeyboardInterrupt:
        _handle_interrupt(exit_direct=True)
        return []
    
    if use_all:
        return [a["profile"] for a in accounts]
    
    # Otherwise, show checkboxes (with all pre-checked)
    try:
        selected = questionary.checkbox(
            f"{ICONS['check']} Uncheck akun yang tidak ingin dipilih:",
            choices=[
                questionary.Choice(
                    title=a.get("display_name") or a["profile"],
                    value=a["profile"],
                    checked=True  # All pre-checked
                )
                for a in accounts
            ],
            style=CUSTOM_STYLE,
            instruction="(Spasi untuk uncheck, Enter untuk konfirmasi)",
        ).ask()
    except KeyboardInterrupt:
        _handle_interrupt(exit_direct=True)
        return []
    
    return selected or []


def _simple_check_select(display_name, configured_checks, available_checks):
    """Simplified check selection with default using customer-configured checks.
    
    Args:
        display_name: Customer display name
        configured_checks: List of check names configured for this customer
        available_checks: Dict of all available check classes
        
    Returns:
        List of selected check names
    """
    if not configured_checks:
        return []
    
    # Filter only valid checks
    valid_checks = [c for c in configured_checks if c in available_checks]
    
    if not valid_checks:
        return []
    
    # Show info
    console.print(
        f"\n[cyan]{display_name}[/cyan] memiliki [yellow]{len(valid_checks)}[/yellow] checks terkonfigurasi"
    )
    console.print(f"[dim]Checks: {', '.join(valid_checks)}[/dim]\n")
    
    # Ask: use all configured checks?
    try:
        use_all = questionary.confirm(
            f"{ICONS['check']} Gunakan semua checks yang terkonfigurasi?",
            default=True,  # Default YES
            style=CUSTOM_STYLE,
        ).ask()
    except KeyboardInterrupt:
        _handle_interrupt(exit_direct=True)
        return []
    
    if use_all:
        return valid_checks
    
    # Otherwise, show checkboxes (with all pre-checked)
    try:
        selected = questionary.checkbox(
            f"{ICONS['check']} Uncheck checks yang tidak ingin dijalankan:",
            choices=[
                questionary.Choice(
                    title=check_name,
                    value=check_name,
                    checked=True  # All pre-checked
                )
                for check_name in valid_checks
            ],
            style=CUSTOM_STYLE,
            instruction="(Spasi untuk uncheck, Enter untuk konfirmasi)",
        ).ask()
    except KeyboardInterrupt:
        _handle_interrupt(exit_direct=True)
        return []
    
    return selected or []


def _choose_region(selected_profiles):
    """Region selection with beautiful UI."""
    default_region = resolve_region(selected_profiles, None)
    region_choices = [
        questionary.Choice("🌏 Jakarta (ap-southeast-3)", value="ap-southeast-3"),
        questionary.Choice("🌏 Singapore (ap-southeast-1)", value="ap-southeast-1"),
        questionary.Choice("🌎 N. Virginia (us-east-1)", value="us-east-1"),
        questionary.Choice("🌎 Oregon (us-west-2)", value="us-west-2"),
        questionary.Choice("⌨️  Custom region...", value="other"),
    ]

    region = _select_prompt(
        f"{ICONS['settings']} Pilih Region",
        region_choices,
        default=default_region,
    )
    if region is None:
        return None
    if region == "other":
        try:
            region = questionary.text(
                "Masukkan region (contoh: eu-west-1):",
                style=CUSTOM_STYLE,
            ).ask()
        except KeyboardInterrupt:
            _handle_interrupt(exit_direct=True)
            return None
    return region


def _pick_profiles(allow_multiple=True):
    """Profile picker with beautiful UI.

    Escape at group/profile picker returns to source picker.
    """
    source_choices = [
        questionary.Choice(
            f"{ICONS['settings']} Group (SSO) - Profil terdaftar", value="group"
        ),
        questionary.Choice(
            f"{ICONS['ec2list']} Local Profiles - AWS CLI config", value="local"
        ),
    ]

    step = "source"
    source = None

    while True:
        if step == "source":
            source = _select_prompt(
                f"{ICONS['settings']} Sumber Profil", source_choices, allow_back=True
            )
            if not source:
                return [], None, True  # back signal to caller

            if source == "local":
                step = "local"
            else:
                step = "group"

        elif step == "group":
            mandatory_groups = {"NABATI-KSNI", "Master"}
            group_choices = [
                questionary.Choice(
                    f"{ICONS['dot']} {name} ({len(profs)} profiles){' (mandatory)' if name in mandatory_groups else ''}",
                    value=name,
                )
                for name, profs in PROFILE_GROUPS.items()
            ]

            group_choice = _select_prompt(
                f"{ICONS['all']} Pilih Group", group_choices, allow_back=True
            )
            if not group_choice:
                # Escape = back to source picker
                step = "source"
                continue

            choices = list(PROFILE_GROUPS[group_choice].keys())
            mandatory_profiles = {"asg"}
            if allow_multiple:
                formatted_choices = [
                    f"{choice} (mandatory)" if choice in mandatory_profiles else choice
                    for choice in choices
                ]
                profiles = _checkbox_prompt(
                    f"{ICONS['check']} Pilih Akun dari {group_choice}",
                    formatted_choices,
                    allow_back=True,
                )
                if profiles is None:
                    # Escape = back to group picker
                    continue
                profiles = profiles or []
                profiles = [p.replace(" (mandatory)", "") for p in profiles]
            else:
                formatted_choices = [
                    f"{choice} (mandatory)" if choice in mandatory_profiles else choice
                    for choice in choices
                ]
                selected = _select_prompt(
                    f"{ICONS['single']} Pilih Akun", formatted_choices, allow_back=True
                )
                if selected is None:
                    continue  # back to group picker
                profiles = [selected.replace(" (mandatory)", "")] if selected else []

            return profiles or [], group_choice, False

        elif step == "local":
            local_profiles = list_local_profiles()
            if not local_profiles:
                print_error(
                    "Tidak menemukan profil AWS lokal. Silakan configure AWS CLI terlebih dulu."
                )
                return [], None, False

            if allow_multiple:
                profiles = _checkbox_prompt(
                    f"{ICONS['check']} Pilih Profil Lokal",
                    local_profiles,
                    allow_back=True,
                )
                if profiles is None:
                    step = "source"
                    continue
            else:
                selected = _select_prompt(
                    f"{ICONS['single']} Pilih Profil", local_profiles, allow_back=True
                )
                if selected is None:
                    step = "source"
                    continue
                profiles = [selected] if selected else []

            return profiles or [], None, False


def _pause():
    """Pause and wait for user input."""
    console.print()
    try:
        questionary.press_any_key_to_continue(
            message="Tekan Enter untuk kembali ke menu utama...",
            style=CUSTOM_STYLE,
        ).ask()
    except (KeyboardInterrupt, AttributeError):
        try:
            questionary.text(
                "Tekan Enter untuk kembali...",
                style=CUSTOM_STYLE,
                default="",
            ).ask()
        except KeyboardInterrupt:
            _handle_interrupt(exit_direct=True)
