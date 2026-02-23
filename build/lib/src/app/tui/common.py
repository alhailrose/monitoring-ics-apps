"""Shared helper utilities for TUI flows."""

import sys
from time import monotonic

import questionary

from src.core.runtime.config import (
    PROFILE_GROUPS,
    INTERRUPT_EXIT_WINDOW,
    CUSTOM_STYLE,
    get_last_interrupt_ts,
    set_last_interrupt_ts,
)
from src.core.runtime.ui import console, print_error, ICONS
from src.core.runtime.utils import list_local_profiles, resolve_region


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


def _select_prompt(prompt, choices, default=None):
    """Beautiful select prompt with icons."""
    try:
        ans = questionary.select(
            prompt,
            choices=choices,
            default=default
            if default in [c if isinstance(c, str) else c.value for c in choices]
            else None,
            style=CUSTOM_STYLE,
            instruction="(Gunakan ↑↓ untuk navigasi, Enter untuk pilih)",
        ).ask()
    except KeyboardInterrupt:
        _handle_interrupt(exit_direct=True)
        return None
    return ans or None


def _checkbox_prompt(prompt, choices):
    """Beautiful checkbox prompt."""
    try:
        ans = questionary.checkbox(
            prompt,
            choices=choices,
            style=CUSTOM_STYLE,
            instruction="(Spasi untuk pilih, Enter untuk konfirmasi)",
        ).ask()
    except KeyboardInterrupt:
        _handle_interrupt(exit_direct=True)
        return None
    return ans or None


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
    """Profile picker with beautiful UI."""
    source_choices = [
        questionary.Choice(
            f"{ICONS['settings']} Group (SSO) - Profil terdaftar", value="group"
        ),
        questionary.Choice(
            f"{ICONS['ec2list']} Local Profiles - AWS CLI config", value="local"
        ),
    ]

    source = _select_prompt(f"{ICONS['settings']} Sumber Profil", source_choices)
    if not source:
        return [], None, True

    profiles = []
    group_choice = None

    if source == "group":
        mandatory_groups = {"NABATI-KSNI", "Master"}
        group_choices = [
            questionary.Choice(
                f"{ICONS['dot']} {name} ({len(profs)} profiles){' (mandatory)' if name in mandatory_groups else ''}",
                value=name,
            )
            for name, profs in PROFILE_GROUPS.items()
        ]

        group_choice = _select_prompt(f"{ICONS['all']} Pilih Group", group_choices)
        if not group_choice:
            return [], None, True

        choices = list(PROFILE_GROUPS[group_choice].keys())
        mandatory_profiles = {"asg"}
        if allow_multiple:
            formatted_choices = [
                f"{choice} (mandatory)" if choice in mandatory_profiles else choice
                for choice in choices
            ]
            profiles = _checkbox_prompt(
                f"{ICONS['check']} Pilih Akun dari {group_choice}", formatted_choices
            )
            profiles = profiles or []
            profiles = [p.replace(" (mandatory)", "") for p in profiles]
        else:
            formatted_choices = [
                f"{choice} (mandatory)" if choice in mandatory_profiles else choice
                for choice in choices
            ]
            selected = _select_prompt(
                f"{ICONS['single']} Pilih Akun", formatted_choices
            )
            profiles = [selected.replace(" (mandatory)", "")] if selected else []
    else:
        local_profiles = list_local_profiles()
        if not local_profiles:
            print_error(
                "Tidak menemukan profil AWS lokal. Silakan configure AWS CLI terlebih dulu."
            )
            return [], None, False

        if allow_multiple:
            profiles = _checkbox_prompt(
                f"{ICONS['check']} Pilih Profil Lokal", local_profiles
            )
        else:
            selected = _select_prompt(f"{ICONS['single']} Pilih Profil", local_profiles)
            profiles = [selected] if selected else []

    return profiles or [], group_choice, False


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
