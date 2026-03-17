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
    assert calls["pause"] == 0


def test_quick_check_runs_individual_check(monkeypatch):
    """Quick Check with 1 check + 1 profile should call run_individual_check."""
    from src.app.tui import common

    selections = iter(["quick", "exit"])
    calls = {"individual": 0}

    monkeypatch.setattr(
        common, "_select_prompt", lambda *args, **kwargs: next(selections)
    )
    monkeypatch.setattr(common, "_pause", lambda: None)
    monkeypatch.setattr(interactive.console, "clear", lambda: None)
    monkeypatch.setattr(interactive, "print_banner", lambda **kwargs: None)
    monkeypatch.setattr(interactive, "_render_main_dashboard", lambda: None)
    monkeypatch.setattr(
        interactive,
        "_run_quick_check",
        lambda: calls.__setitem__("individual", calls["individual"] + 1),
    )

    interactive.run_interactive()

    assert calls["individual"] == 1


def test_customer_report_dispatches_flow(monkeypatch):
    """Customer Report menu should dispatch to customer flow."""
    from src.app.tui import common

    selections = iter(["customer", "exit"])
    calls = {"customer": 0, "pause": 0}

    monkeypatch.setattr(
        common, "_select_prompt", lambda *args, **kwargs: next(selections)
    )
    monkeypatch.setattr(
        common, "_pause", lambda: calls.__setitem__("pause", calls["pause"] + 1)
    )
    monkeypatch.setattr(interactive.console, "clear", lambda: None)
    monkeypatch.setattr(interactive, "print_banner", lambda **kwargs: None)
    monkeypatch.setattr(interactive, "_render_main_dashboard", lambda: None)

    def _fake_customer_report():
        calls["customer"] += 1
        return True

    monkeypatch.setattr(interactive, "run_customer_report", _fake_customer_report)

    interactive.run_interactive()

    assert calls["customer"] == 1
    assert calls["pause"] == 0


def test_customer_report_cancelled_does_not_pause(monkeypatch):
    """Jika user cancel/back dari Customer Report, jangan tampilkan pause."""
    from src.app.tui import common

    selections = iter(["customer", "exit"])
    calls = {"customer": 0, "pause": 0}

    monkeypatch.setattr(
        common, "_select_prompt", lambda *args, **kwargs: next(selections)
    )
    monkeypatch.setattr(
        common, "_pause", lambda: calls.__setitem__("pause", calls["pause"] + 1)
    )
    monkeypatch.setattr(interactive.console, "clear", lambda: None)
    monkeypatch.setattr(interactive, "print_banner", lambda **kwargs: None)
    monkeypatch.setattr(interactive, "_render_main_dashboard", lambda: None)

    def _fake_customer_report():
        calls["customer"] += 1
        return False

    monkeypatch.setattr(interactive, "run_customer_report", _fake_customer_report)

    interactive.run_interactive()

    assert calls["customer"] == 1
    assert calls["pause"] == 0


def test_main_menu_shows_huawei_check_label(monkeypatch):
    from src.app.tui import common

    captured = {"values": []}

    def _fake_select_prompt(_message, choices):
        captured["values"] = [choice.value for choice in choices]
        return "exit"

    monkeypatch.setattr(common, "_select_prompt", _fake_select_prompt)
    monkeypatch.setattr(interactive.console, "clear", lambda: None)
    monkeypatch.setattr(interactive, "print_banner", lambda **kwargs: None)
    monkeypatch.setattr(interactive, "_render_main_dashboard", lambda: None)

    interactive.run_interactive()

    assert "huawei_check" in captured["values"]
    assert "huawei_util" not in captured["values"]


def test_selecting_huawei_menu_opens_utilization_submenu(monkeypatch):
    from src.app.tui import common

    prompt_values = []
    selections = iter(["huawei_check", "utilization", "exit"])

    def _fake_select_prompt(_message, choices, **_kwargs):
        available_values = [choice.value for choice in choices]
        prompt_values.append(available_values)
        selected = next(selections)
        assert selected in available_values
        return selected

    monkeypatch.setattr(common, "_select_prompt", _fake_select_prompt)
    monkeypatch.setattr(common, "_pause", lambda: None)
    monkeypatch.setattr(interactive.console, "clear", lambda: None)
    monkeypatch.setattr(interactive, "print_banner", lambda **kwargs: None)
    monkeypatch.setattr(interactive, "_render_main_dashboard", lambda: None)

    interactive.run_interactive()

    assert any("utilization" in values for values in prompt_values)


def test_huawei_utilization_runs_consolidated_over_fixed_profiles(monkeypatch):
    from src.app.tui import common

    expected_profiles = interactive.HUAWEI_FIXED_PROFILES
    selections = iter(["huawei_check", "utilization", "exit"])
    calls = []

    monkeypatch.setattr(
        common, "_select_prompt", lambda *_args, **_kwargs: next(selections)
    )
    monkeypatch.setattr(common, "_pause", lambda: None)
    monkeypatch.setattr(interactive.console, "clear", lambda: None)
    monkeypatch.setattr(interactive, "print_banner", lambda **kwargs: None)
    monkeypatch.setattr(interactive, "_render_main_dashboard", lambda: None)
    monkeypatch.setattr(
        interactive,
        "run_group_specific",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("run_group_specific should not be used")
        ),
    )
    monkeypatch.setattr(
        interactive,
        "run_individual_check",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("run_individual_check should not be used")
        ),
    )

    def _fake_run_all_checks(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(interactive, "run_all_checks", _fake_run_all_checks)

    interactive.run_interactive()

    assert len(calls) == 1

    call_kwargs = calls[0]
    assert call_kwargs["profiles"] == expected_profiles
    assert call_kwargs["group_name"] == "Huawei"
    assert call_kwargs["region"] == "ap-southeast-4"
    assert set(call_kwargs["checks_override"]) == {"huawei-ecs-util"}
    assert call_kwargs["output_mode"] == "huawei_legacy"


def test_selecting_huawei_submenu_back_does_not_run_checks(monkeypatch):
    from src.app.tui import common

    selections = iter(["huawei_check", "back", "exit"])
    prompt_values = []

    def _fake_select_prompt(_message, choices, **_kwargs):
        available_values = [choice.value for choice in choices]
        prompt_values.append(available_values)
        return next(selections)

    monkeypatch.setattr(common, "_select_prompt", _fake_select_prompt)
    monkeypatch.setattr(common, "_pause", lambda: None)
    monkeypatch.setattr(interactive.console, "clear", lambda: None)
    monkeypatch.setattr(interactive, "print_banner", lambda **kwargs: None)
    monkeypatch.setattr(interactive, "_render_main_dashboard", lambda: None)
    monkeypatch.setattr(
        interactive,
        "run_all_checks",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("run_all_checks should not be called when choosing back")
        ),
    )

    interactive.run_interactive()

    assert any("back" in values for values in prompt_values)


def test_huawei_utilization_shows_error_when_check_not_registered(monkeypatch):
    errors = []

    monkeypatch.setitem(interactive.AVAILABLE_CHECKS, "huawei-ecs-util", None)
    monkeypatch.setattr(
        interactive,
        "run_all_checks",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("run_all_checks should not run when checker is missing")
        ),
    )
    monkeypatch.setattr(interactive, "print_mini_banner", lambda: None)
    monkeypatch.setattr(
        interactive, "print_section_header", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        interactive, "print_error", lambda message: errors.append(message)
    )

    interactive.run_huawei_utilization()

    assert errors
    assert "huawei-ecs-util" in errors[0]


def test_check_choices_do_not_include_daily_arbel():
    """CHECK_CHOICES should not include daily-arbel (it's customer-specific)."""
    check_values = [c.value for c in interactive.CHECK_CHOICES]
    assert "daily-arbel" not in check_values


def test_pick_profiles_all_accounts_returns_all_profiles(monkeypatch):
    """All Accounts mode should return every profile from every customer."""
    from src.app.tui import common
    from src.configs import loader

    monkeypatch.setattr(
        loader,
        "list_customers",
        lambda: [
            {"customer_id": "nabati", "display_name": "Nabati", "account_count": 2},
            {"customer_id": "diamond", "display_name": "Diamond", "account_count": 1},
        ],
    )

    def _fake_load(customer_id):
        if customer_id == "nabati":
            return {"accounts": [{"profile": "ksni-master"}, {"profile": "erp-ksni"}]}
        return {"accounts": [{"profile": "Diamond"}]}

    monkeypatch.setattr(loader, "load_customer_config", _fake_load)

    # User picks "all_accounts" mode
    monkeypatch.setattr(
        common, "_select_prompt", lambda _msg, _choices, **_kw: "all_accounts"
    )

    profiles, group_name, back = interactive._pick_profiles_from_customers()

    assert not back
    assert sorted(profiles) == ["Diamond", "erp-ksni", "ksni-master"]
    assert group_name == "All Accounts"


def test_pick_profiles_per_customer_all_accounts(monkeypatch):
    """Per Customer mode with 'pilih semua' should return all profiles of selected customer."""
    from src.app.tui import common
    from src.configs import loader

    monkeypatch.setattr(
        loader,
        "list_customers",
        lambda: [
            {"customer_id": "nabati", "display_name": "Nabati", "account_count": 2}
        ],
    )
    monkeypatch.setattr(
        loader,
        "load_customer_config",
        lambda _: {"accounts": [{"profile": "ksni-master"}, {"profile": "erp-ksni"}]},
    )

    select_calls = iter(["per_customer", "nabati"])
    monkeypatch.setattr(
        common, "_select_prompt", lambda _msg, _choices, **_kw: next(select_calls)
    )

    # confirm "pilih semua" → True
    import questionary as q

    monkeypatch.setattr(
        q, "confirm", lambda *_a, **_kw: type("C", (), {"ask": lambda self: True})()
    )

    profiles, group_name, back = interactive._pick_profiles_from_customers()

    assert not back
    assert sorted(profiles) == ["erp-ksni", "ksni-master"]
    assert group_name == "Nabati"


def test_pick_profiles_per_customer_partial_selection(monkeypatch):
    """Per Customer mode with manual select should return only checked profiles."""
    from src.app.tui import common
    from src.configs import loader

    monkeypatch.setattr(
        loader,
        "list_customers",
        lambda: [
            {"customer_id": "nabati", "display_name": "Nabati", "account_count": 2}
        ],
    )
    monkeypatch.setattr(
        loader,
        "load_customer_config",
        lambda _: {"accounts": [{"profile": "ksni-master"}, {"profile": "erp-ksni"}]},
    )

    select_calls = iter(["per_customer", "nabati"])
    monkeypatch.setattr(
        common, "_select_prompt", lambda _msg, _choices, **_kw: next(select_calls)
    )

    import questionary as q

    monkeypatch.setattr(
        q, "confirm", lambda *_a, **_kw: type("C", (), {"ask": lambda self: False})()
    )
    monkeypatch.setattr(
        common, "_checkbox_prompt", lambda _msg, _choices, **_kw: ["ksni-master"]
    )

    profiles, group_name, back = interactive._pick_profiles_from_customers()

    assert not back
    assert profiles == ["ksni-master"]
    assert group_name == "Nabati"


def test_pick_profiles_per_customer_back_from_customer_to_mode(monkeypatch):
    """Escape di 'pilih customer' harus kembali ke mode selector, bukan keluar."""
    from src.app.tui import common
    from src.configs import loader

    monkeypatch.setattr(
        loader,
        "list_customers",
        lambda: [
            {"customer_id": "nabati", "display_name": "Nabati", "account_count": 2}
        ],
    )
    monkeypatch.setattr(
        loader,
        "load_customer_config",
        lambda _: {"accounts": [{"profile": "ksni-master"}, {"profile": "erp-ksni"}]},
    )

    # First loop: per_customer, then None (escape customer pick)
    # Second loop: all_accounts (user corrects their choice)
    call_seq = iter(["per_customer", None, "all_accounts"])
    monkeypatch.setattr(
        common, "_select_prompt", lambda _msg, _choices, **_kw: next(call_seq)
    )

    profiles, group_name, back = interactive._pick_profiles_from_customers()

    assert not back
    assert group_name == "All Accounts"
    assert len(profiles) == 2


def test_quick_check_back_from_profile_to_check_picker(monkeypatch):
    """Saat akun kosong, Quick Check harus tetap di picker akun dengan peringatan."""
    monkeypatch.setattr(interactive, "print_mini_banner", lambda: None)
    monkeypatch.setattr(interactive, "print_section_header", lambda *a, **kw: None)

    from src.app.tui import common

    pick_calls = {"count": 0}
    check_calls = []
    errors = []

    # _pick_profiles_from_customers: first call returns empty, second returns profile
    def fake_pick():
        pick_calls["count"] += 1
        if pick_calls["count"] == 1:
            return [], None, False
        return ["prod-a"], "Nabati", False

    monkeypatch.setattr(interactive, "_pick_profiles_from_customers", fake_pick)

    select_calls = iter(["health"])
    monkeypatch.setattr(
        common, "_select_prompt", lambda _msg, _choices, **_kw: next(select_calls)
    )
    monkeypatch.setattr(common, "_choose_region", lambda profiles: "ap-southeast-3")
    monkeypatch.setattr(
        interactive, "print_error", lambda message: errors.append(message)
    )
    monkeypatch.setattr(
        interactive,
        "run_individual_check",
        lambda check, profile, region, **kw: check_calls.append((check, profile)),
    )

    interactive._run_quick_check()

    assert pick_calls["count"] == 2, "profile picker harus dipanggil ulang"
    assert check_calls == [("health", "prod-a")]
    assert errors and "Pilih minimal satu akun" in errors[-1]


def test_check_choices_include_aws_utilization_3core():
    values = [c.value for c in interactive.CHECK_CHOICES]
    assert "aws-utilization-3core" in values


def test_main_menu_hides_aws_utilization_label(monkeypatch):
    from src.app.tui import common

    captured = {"values": []}

    def _fake_select_prompt(_message, choices):
        captured["values"] = [choice.value for choice in choices]
        return "exit"

    monkeypatch.setattr(common, "_select_prompt", _fake_select_prompt)
    monkeypatch.setattr(interactive.console, "clear", lambda: None)
    monkeypatch.setattr(interactive, "print_banner", lambda **kwargs: None)
    monkeypatch.setattr(interactive, "_render_main_dashboard", lambda: None)

    interactive.run_interactive()

    assert "aws_utilization" not in captured["values"]


def test_run_aws_utilization_trial_runs_with_sadewa_profiles(monkeypatch):
    calls = []
    sso_args = []

    monkeypatch.setattr(interactive, "print_mini_banner", lambda: None)
    monkeypatch.setattr(
        interactive, "print_section_header", lambda *_args, **_kwargs: None
    )

    def _fake_collect(sso_session=None):
        sso_args.append(sso_session)
        return ["Diamond", "KKI"]

    monkeypatch.setattr(interactive, "collect_customer_profiles", _fake_collect)
    monkeypatch.setitem(interactive.AVAILABLE_CHECKS, "aws-utilization-3core", object())
    monkeypatch.setattr(
        interactive, "run_all_checks", lambda **kwargs: calls.append(kwargs)
    )

    interactive.run_aws_utilization(trial_mode=True)

    assert sso_args == ["sadewa-sso"]
    assert len(calls) == 1
    assert calls[0]["profiles"] == ["Diamond", "KKI"]
    assert set(calls[0]["checks_override"]) == {"aws-utilization-3core"}


def test_run_aws_utilization_all_customers_runs_without_sso_filter(monkeypatch):
    calls = []
    sso_args = []

    monkeypatch.setattr(interactive, "print_mini_banner", lambda: None)
    monkeypatch.setattr(
        interactive, "print_section_header", lambda *_args, **_kwargs: None
    )

    def _fake_collect(sso_session=None):
        sso_args.append(sso_session)
        return ["programa", "ucoal-prod"]

    monkeypatch.setattr(interactive, "collect_customer_profiles", _fake_collect)
    monkeypatch.setitem(interactive.AVAILABLE_CHECKS, "aws-utilization-3core", object())
    monkeypatch.setattr(
        interactive, "run_all_checks", lambda **kwargs: calls.append(kwargs)
    )

    interactive.run_aws_utilization(trial_mode=False)

    assert sso_args == [None]
    assert len(calls) == 1
    assert calls[0]["profiles"] == ["programa", "ucoal-prod"]
    assert set(calls[0]["checks_override"]) == {"aws-utilization-3core"}
