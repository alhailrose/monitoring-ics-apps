from src.app.tui import interactive
from src.app.tui import bootstrap


def test_run_interactive_v2_delegates_to_run_interactive(monkeypatch):
    called = {"ok": False}

    def _fake_run_interactive():
        called["ok"] = True

    monkeypatch.setattr(interactive, "run_interactive", _fake_run_interactive)

    interactive.run_interactive_v2()

    assert called["ok"] is True


def test_run_interactive_v2_is_callable():
    assert callable(interactive.run_interactive_v2)


def test_bootstrap_run_interactive_delegates_to_interactive(monkeypatch):
    called = {"ok": False}

    def _fake_run_interactive():
        called["ok"] = True

    monkeypatch.setattr(interactive, "run_interactive", _fake_run_interactive)

    bootstrap.run_interactive()

    assert called["ok"] is True


def test_bootstrap_run_interactive_v2_delegates_to_interactive(monkeypatch):
    called = {"ok": False}

    def _fake_run_interactive_v2():
        called["ok"] = True

    monkeypatch.setattr(interactive, "run_interactive_v2", _fake_run_interactive_v2)

    bootstrap.run_interactive_v2()

    assert called["ok"] is True


def test_interactive_reexports_common_helpers():
    from src.app.tui import common

    assert interactive._select_prompt is common._select_prompt
    assert interactive._pause is common._pause


def test_run_interactive_uses_common_prompt_and_pause(monkeypatch):
    from src.app.tui import common

    selections = iter(["settings", "exit"])
    calls = {"settings": 0, "pause": 0}

    monkeypatch.setattr(
        common, "_select_prompt", lambda *args, **kwargs: next(selections)
    )
    monkeypatch.setattr(
        common, "_pause", lambda: calls.__setitem__("pause", calls["pause"] + 1)
    )
    monkeypatch.setattr(interactive.console, "clear", lambda: None)
    monkeypatch.setattr(interactive, "print_banner", lambda **kwargs: None)
    monkeypatch.setattr(interactive, "_render_main_dashboard", lambda: None)
    monkeypatch.setattr(
        interactive,
        "run_settings_menu",
        lambda: calls.__setitem__("settings", calls["settings"] + 1),
    )

    interactive.run_interactive()

    assert calls["settings"] == 1
    assert calls["pause"] == 1


def test_run_interactive_dispatches_settings_flow_module(monkeypatch):
    from src.app.tui import common
    from src.app.tui.flows import settings as settings_flow

    selections = iter(["settings", "exit"])
    calls = {"settings": 0, "pause": 0}

    monkeypatch.setattr(
        common, "_select_prompt", lambda *args, **kwargs: next(selections)
    )
    monkeypatch.setattr(
        common, "_pause", lambda: calls.__setitem__("pause", calls["pause"] + 1)
    )
    monkeypatch.setattr(interactive.console, "clear", lambda: None)
    monkeypatch.setattr(interactive, "print_banner", lambda **kwargs: None)
    monkeypatch.setattr(interactive, "_render_main_dashboard", lambda: None)
    monkeypatch.setattr(
        settings_flow,
        "run_settings_menu",
        lambda *args, **kwargs: calls.__setitem__("settings", calls["settings"] + 1),
    )

    interactive.run_interactive()

    assert calls["settings"] == 1
    assert calls["pause"] == 1


def test_run_interactive_dispatches_cw_cost_flow_module(monkeypatch):
    from src.app.tui import common
    from src.app.tui.flows import cloudwatch_cost

    selections = iter(["cw_cost", "exit"])
    calls = {"cost": 0, "pause": 0}

    monkeypatch.setattr(
        common, "_select_prompt", lambda *args, **kwargs: next(selections)
    )
    monkeypatch.setattr(
        common, "_pause", lambda: calls.__setitem__("pause", calls["pause"] + 1)
    )
    monkeypatch.setattr(interactive.console, "clear", lambda: None)
    monkeypatch.setattr(interactive, "print_banner", lambda **kwargs: None)
    monkeypatch.setattr(interactive, "_render_main_dashboard", lambda: None)
    monkeypatch.setattr(
        cloudwatch_cost,
        "run_cloudwatch_cost_report",
        lambda: calls.__setitem__("cost", calls["cost"] + 1),
    )

    interactive.run_interactive()

    assert calls["cost"] == 1
    assert calls["pause"] == 1


def test_single_check_cost_runs_individual_check(monkeypatch):
    from src.app.tui import common

    selections = iter(["single", "cost", "exit"])
    calls = {"individual": 0}

    monkeypatch.setattr(
        common, "_select_prompt", lambda *args, **kwargs: next(selections)
    )
    monkeypatch.setattr(
        common, "_pick_profiles", lambda **kwargs: (["acct-a"], None, False)
    )
    monkeypatch.setattr(common, "_choose_region", lambda profiles: "ap-southeast-3")
    monkeypatch.setattr(common, "_pause", lambda: None)
    monkeypatch.setattr(interactive.console, "clear", lambda: None)
    monkeypatch.setattr(interactive, "print_banner", lambda **kwargs: None)
    monkeypatch.setattr(interactive, "print_mini_banner", lambda: None)
    monkeypatch.setattr(
        interactive, "print_section_header", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(interactive, "_render_main_dashboard", lambda: None)
    monkeypatch.setattr(interactive, "_render_single_check_dashboard", lambda: None)
    monkeypatch.setattr(
        interactive,
        "run_individual_check",
        lambda *args, **kwargs: calls.__setitem__(
            "individual", calls["individual"] + 1
        ),
    )
    monkeypatch.setattr(
        interactive,
        "run_all_checks",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("single check must not call run_all_checks")
        ),
    )

    interactive.run_interactive()

    assert calls["individual"] == 1


def test_single_check_menu_does_not_offer_daily_arbel(monkeypatch):
    from src.app.tui import common

    captured = {"check_values": []}
    selections = iter(["single", None, "exit"])

    def _fake_select(_prompt, choices, default=None):
        if not captured["check_values"] and any(
            hasattr(choice, "value") and choice.value == "health" for choice in choices
        ):
            captured["check_values"] = [choice.value for choice in choices]
        return next(selections)

    monkeypatch.setattr(common, "_select_prompt", _fake_select)
    monkeypatch.setattr(common, "_pause", lambda: None)
    monkeypatch.setattr(interactive.console, "clear", lambda: None)
    monkeypatch.setattr(interactive, "print_banner", lambda **kwargs: None)
    monkeypatch.setattr(interactive, "_render_main_dashboard", lambda: None)
    monkeypatch.setattr(interactive, "_render_single_check_dashboard", lambda: None)

    interactive.run_interactive()

    assert "daily-arbel" not in captured["check_values"]
