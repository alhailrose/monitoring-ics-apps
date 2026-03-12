from types import SimpleNamespace

import pytest

from src.app.tui.flows import customer
from src.app.tui import interactive


def _checker_factory(supports_consolidated=False):
    return lambda region="": SimpleNamespace(
        supports_consolidated=supports_consolidated
    )


def test_run_generic_customer_uses_searchable_selectors(monkeypatch):
    cfg = {
        "customer_id": "acme",
        "display_name": "Acme",
        "checks": ["health", "cost"],
        "accounts": [
            {"profile": "prod-a", "region": "ap-southeast-3"},
            {"profile": "prod-b", "region": "us-east-1"},
        ],
    }
    selector_calls = []
    group_calls = []

    monkeypatch.setattr(
        customer,
        "AVAILABLE_CHECKS",
        {
            "health": _checker_factory(supports_consolidated=False),
            "cost": _checker_factory(supports_consolidated=False),
        },
    )

    def fake_multi_select(prompt, choices, ask_search=True):
        selector_calls.append((prompt, list(choices), ask_search))
        if "Checks" in prompt:
            return ["health"]
        return ["prod-a"]

    monkeypatch.setattr(
        customer.common, "_searchable_multi_select_prompt", fake_multi_select
    )
    monkeypatch.setattr(customer, "run_all_checks", lambda **kwargs: None)
    monkeypatch.setattr(
        customer,
        "run_group_specific",
        lambda *args, **kwargs: group_calls.append((args, kwargs)),
    )

    result = customer._run_generic_customer(cfg)

    assert result == {"customer_id": "acme", "checks": ["health"]}
    assert selector_calls[0][1] == ["health", "cost"]
    assert selector_calls[1][1] == ["prod-a", "prod-b"]
    assert len(group_calls) == 1
    assert group_calls[0][0][0] == "health"
    assert group_calls[0][0][1] == ["prod-a"]


def test_run_generic_customer_returns_none_on_empty_check_selection(monkeypatch):
    cfg = {
        "customer_id": "acme",
        "display_name": "Acme",
        "checks": ["health"],
        "accounts": [{"profile": "prod-a", "region": "ap-southeast-3"}],
    }
    errors = []

    monkeypatch.setattr(customer, "AVAILABLE_CHECKS", {"health": _checker_factory()})
    monkeypatch.setattr(
        customer.common,
        "_searchable_multi_select_prompt",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(customer, "print_error", lambda message: errors.append(message))

    result = customer._run_generic_customer(cfg)

    assert result is None
    assert errors[-1] == "Tidak ada check dipilih."


def test_run_generic_customer_returns_none_on_empty_account_selection(monkeypatch):
    cfg = {
        "customer_id": "acme",
        "display_name": "Acme",
        "checks": ["health"],
        "accounts": [{"profile": "prod-a", "region": "ap-southeast-3"}],
    }
    errors = []

    monkeypatch.setattr(customer, "AVAILABLE_CHECKS", {"health": _checker_factory()})

    call_index = {"value": 0}

    def fake_multi_select(*args, **kwargs):
        call_index["value"] += 1
        if call_index["value"] == 1:
            return ["health"]
        return []

    monkeypatch.setattr(
        customer.common, "_searchable_multi_select_prompt", fake_multi_select
    )
    monkeypatch.setattr(customer, "print_error", lambda message: errors.append(message))

    result = customer._run_generic_customer(cfg)

    assert result is None
    assert errors[-1] == "Tidak ada akun dipilih."


def test_run_generic_customer_injects_alarm_names_for_alarm_verification(monkeypatch):
    cfg = {
        "customer_id": "acme",
        "display_name": "Acme",
        "checks": ["alarm_verification"],
        "accounts": [
            {"profile": "prod-a", "region": "ap-southeast-3"},
            {"profile": "prod-b", "region": "ap-southeast-3"},
        ],
    }
    calls = []

    monkeypatch.setattr(
        customer,
        "AVAILABLE_CHECKS",
        {"alarm_verification": _checker_factory(supports_consolidated=False)},
    )

    call_index = {"value": 0}

    def fake_multi_select(*args, **kwargs):
        call_index["value"] += 1
        if call_index["value"] == 1:
            return ["alarm_verification"]
        return ["prod-a", "prod-b"]

    monkeypatch.setattr(
        customer.common, "_searchable_multi_select_prompt", fake_multi_select
    )
    monkeypatch.setattr(
        customer,
        "get_alarm_names_for_profile",
        lambda profile: [f"alarm-{profile}", "shared-alarm"],
    )
    monkeypatch.setattr(
        customer,
        "run_group_specific",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    result = customer._run_generic_customer(cfg)

    assert result == {"customer_id": "acme", "checks": ["alarm_verification"]}
    assert len(calls) == 1
    assert calls[0][0][0] == "alarm_verification"
    assert calls[0][1]["check_kwargs"]["min_duration_minutes"] == 10
    assert sorted(calls[0][1]["check_kwargs"]["alarm_names"]) == [
        "alarm-prod-a",
        "alarm-prod-b",
        "shared-alarm",
    ]


def test_run_customer_report_filters_customer_choices_by_keyword(monkeypatch):
    customers = [
        {
            "customer_id": "alpha",
            "display_name": "Alpha",
            "account_count": 1,
            "checks": [],
            "slack_enabled": False,
        },
        {
            "customer_id": "bravo",
            "display_name": "Bravo",
            "account_count": 2,
            "checks": [],
            "slack_enabled": False,
        },
    ]
    captured = {}
    select_calls = {"count": 0}

    monkeypatch.setattr(customer, "print_mini_banner", lambda: None)
    monkeypatch.setattr(customer, "print_section_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        customer, "_render_customer_dashboard", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(customer, "list_customers", lambda: customers)

    monkeypatch.setattr(
        customer.questionary,
        "text",
        lambda *args, **kwargs: SimpleNamespace(ask=lambda: "alp"),
    )

    def fake_select(prompt, choices, default=None, **kwargs):
        select_calls["count"] += 1
        if select_calls["count"] == 1:
            # First call: mode selection — pick "single"
            return "single"
        # Second call: customer picker — capture and return None (escape)
        # Subsequent calls (mode picker re-shown after back nav) → None (exit)
        if "prompt" not in captured:
            captured["prompt"] = prompt
            captured["values"] = [choice.value for choice in choices]
        return None

    monkeypatch.setattr(customer.common, "_select_prompt", fake_select)

    customer.run_customer_report()

    assert captured["prompt"].endswith("Pilih Customer")
    assert captured["values"] == ["alpha"]


def test_quick_check_uses_customer_mapping_profiles_only(monkeypatch):
    select_calls = []
    picker_calls = {"count": 0}
    individual_calls = []

    monkeypatch.setattr(interactive, "print_mini_banner", lambda: None)
    monkeypatch.setattr(
        interactive, "print_section_header", lambda *args, **kwargs: None
    )

    def fake_select(*args, **kwargs):
        select_calls.append(args[0])
        if len(select_calls) > 1:
            raise AssertionError("Source selector should not be shown in quick check")
        return "health"

    monkeypatch.setattr(interactive.common, "_select_prompt", fake_select)

    def fake_pick_profiles_from_customers():
        picker_calls["count"] += 1
        return ["prod-a"], "All Customers", False

    monkeypatch.setattr(
        interactive, "_pick_profiles_from_customers", fake_pick_profiles_from_customers
    )
    monkeypatch.setattr(
        interactive.common, "_choose_region", lambda profiles: "ap-southeast-3"
    )
    monkeypatch.setattr(
        interactive,
        "run_individual_check",
        lambda check, profile, region: individual_calls.append(
            (check, profile, region)
        ),
    )

    interactive._run_quick_check()

    assert picker_calls["count"] == 1
    assert len(select_calls) == 1
    assert individual_calls == [("health", "prod-a", "ap-southeast-3")]


def test_pick_profiles_from_customers_uses_mode_selector(monkeypatch):
    """_pick_profiles_from_customers should show a mode selector (All Accounts / Per Customer)."""
    customers = [
        {"customer_id": "acme", "display_name": "Acme", "account_count": 1},
        {"customer_id": "globex", "display_name": "Globex", "account_count": 1},
    ]

    cfg_by_customer = {
        "acme": {"accounts": [{"profile": "prod-a", "display_name": "Prod A"}]},
        "globex": {"accounts": [{"profile": "prod-b", "display_name": "Prod B"}]},
    }

    monkeypatch.setattr("src.configs.loader.list_customers", lambda: customers)
    monkeypatch.setattr(
        "src.configs.loader.load_customer_config",
        lambda customer_id: cfg_by_customer[customer_id],
    )

    # User picks "all_accounts" mode
    monkeypatch.setattr(
        interactive.common,
        "_select_prompt",
        lambda _msg, _choices, **_kw: "all_accounts",
    )
    monkeypatch.setattr(
        interactive.common,
        "_checkbox_prompt",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("Checkbox should not be used in all_accounts mode")
        ),
    )

    profiles, group_choice, back = interactive._pick_profiles_from_customers()

    assert back is False
    assert group_choice == "All Accounts"
    assert sorted(profiles) == ["prod-a", "prod-b"]


def test_run_customer_report_back_from_customer_picker_to_mode(monkeypatch):
    """Escape di customer picker harus kembali ke mode selector."""
    customers = [
        {
            "customer_id": "alpha",
            "display_name": "Alpha",
            "account_count": 1,
            "checks": [],
            "slack_enabled": False,
        },
    ]

    monkeypatch.setattr(customer, "print_mini_banner", lambda: None)
    monkeypatch.setattr(customer, "print_section_header", lambda *a, **kw: None)
    monkeypatch.setattr(customer, "_render_customer_dashboard", lambda *a: None)
    monkeypatch.setattr(customer, "list_customers", lambda: customers)
    monkeypatch.setattr(
        customer.questionary,
        "text",
        lambda *a, **kw: SimpleNamespace(ask=lambda: ""),
    )

    select_seq = iter(
        [
            "single",  # mode picker: single
            None,  # customer picker: escape → back to mode
            None,  # mode picker: escape → exit flow
        ]
    )
    monkeypatch.setattr(
        customer.common,
        "_select_prompt",
        lambda _msg, _choices, **_kw: next(select_seq),
    )

    # Should complete without raising or hanging
    customer.run_customer_report()
