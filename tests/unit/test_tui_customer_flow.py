from types import SimpleNamespace

import pytest

from backend.interfaces.cli.flows import customer
from backend.interfaces.cli import interactive


def _checker_factory(supports_consolidated=False):
    return lambda region="": SimpleNamespace(
        supports_consolidated=supports_consolidated
    )


def test_run_generic_customer_uses_checkbox_selectors(monkeypatch):
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

    def fake_checkbox(prompt, choices, **kwargs):
        selector_calls.append((prompt, [c.value for c in choices]))
        if "Checks" in prompt:
            return ["health"]
        return ["prod-a"]

    monkeypatch.setattr(customer.common, "_checkbox_prompt", fake_checkbox)
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


def test_run_generic_customer_prompts_again_on_empty_check_selection(monkeypatch):
    cfg = {
        "customer_id": "acme",
        "display_name": "Acme",
        "checks": ["health"],
        "accounts": [{"profile": "prod-a", "region": "ap-southeast-3"}],
    }
    errors = []

    monkeypatch.setattr(customer, "AVAILABLE_CHECKS", {"health": _checker_factory()})

    call_index = {"value": 0}

    def fake_checkbox(*args, **kwargs):
        call_index["value"] += 1
        if call_index["value"] == 1:
            return []
        if call_index["value"] == 2:
            return ["health"]
        return ["prod-a"]

    monkeypatch.setattr(customer.common, "_checkbox_prompt", fake_checkbox)
    monkeypatch.setattr(customer, "print_error", lambda message: errors.append(message))
    group_calls = []
    monkeypatch.setattr(
        customer,
        "run_group_specific",
        lambda *args, **kwargs: group_calls.append((args, kwargs)),
    )

    result = customer._run_generic_customer(cfg)

    assert result == {"customer_id": "acme", "checks": ["health"]}
    assert errors[-1] == "Tidak ada check dipilih."
    assert len(group_calls) == 1


def test_run_generic_customer_prompts_again_on_empty_account_selection(monkeypatch):
    cfg = {
        "customer_id": "acme",
        "display_name": "Acme",
        "checks": ["health"],
        "accounts": [{"profile": "prod-a", "region": "ap-southeast-3"}],
    }
    errors = []

    monkeypatch.setattr(customer, "AVAILABLE_CHECKS", {"health": _checker_factory()})

    call_index = {"value": 0}

    def fake_checkbox(*args, **kwargs):
        call_index["value"] += 1
        if call_index["value"] == 1:
            return ["health"]
        if call_index["value"] == 2:
            return []
        return ["prod-a"]

    monkeypatch.setattr(customer.common, "_checkbox_prompt", fake_checkbox)
    monkeypatch.setattr(customer, "print_error", lambda message: errors.append(message))
    group_calls = []
    monkeypatch.setattr(
        customer,
        "run_group_specific",
        lambda *args, **kwargs: group_calls.append((args, kwargs)),
    )

    result = customer._run_generic_customer(cfg)

    assert result == {"customer_id": "acme", "checks": ["health"]}
    assert errors[-1] == "Tidak ada akun dipilih."
    assert len(group_calls) == 1


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

    def fake_checkbox(*args, **kwargs):
        call_index["value"] += 1
        if call_index["value"] == 1:
            return ["alarm_verification"]
        return ["prod-a", "prod-b"]

    monkeypatch.setattr(customer.common, "_checkbox_prompt", fake_checkbox)
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


def test_run_generic_customer_summary_mode_passes_output_mode_and_regions(monkeypatch):
    cfg = {
        "customer_id": "techmeister",
        "display_name": "Techmeister",
        "check_mode": "summary",
        "checks": ["aws-utilization-3core", "cloudwatch"],
        "accounts": [
            {
                "profile": "Techmeister",
                "regions": ["ap-southeast-1", "eu-central-1", "ap-southeast-3"],
            }
        ],
    }
    calls = []

    monkeypatch.setattr(
        customer,
        "AVAILABLE_CHECKS",
        {
            "aws-utilization-3core": _checker_factory(supports_consolidated=True),
            "cloudwatch": _checker_factory(supports_consolidated=True),
        },
    )

    select_state = {"n": 0}

    def fake_checkbox(*_args, **_kwargs):
        select_state["n"] += 1
        if select_state["n"] == 1:
            return ["aws-utilization-3core", "cloudwatch"]
        return ["Techmeister"]

    monkeypatch.setattr(customer.common, "_checkbox_prompt", fake_checkbox)
    monkeypatch.setattr(
        customer,
        "run_all_checks",
        lambda **kwargs: calls.append(kwargs),
    )
    monkeypatch.setattr(customer, "run_group_specific", lambda *args, **kwargs: None)

    result = customer._run_generic_customer(cfg)

    assert result == {
        "customer_id": "techmeister",
        "checks": ["aws-utilization-3core", "cloudwatch"],
    }
    assert len(calls) == 1
    assert calls[0]["output_mode"] == "summary"
    assert calls[0]["check_kwargs_by_name"] == {
        "aws-utilization-3core": {
            "profile_regions": {
                "Techmeister": ["ap-southeast-1", "eu-central-1", "ap-southeast-3"]
            }
        }
    }


def test_run_generic_customer_back_from_account_selection_returns_back(monkeypatch):
    cfg = {
        "customer_id": "acme",
        "display_name": "Acme",
        "checks": ["health"],
        "accounts": [{"profile": "prod-a", "region": "ap-southeast-3"}],
    }

    monkeypatch.setattr(customer, "AVAILABLE_CHECKS", {"health": _checker_factory()})

    selections = iter([["health"], None, None])
    monkeypatch.setattr(
        customer.common, "_checkbox_prompt", lambda *args, **kwargs: next(selections)
    )

    result = customer._run_generic_customer(cfg)

    assert result == {"back": True}


def test_run_customer_report_uses_checkbox_picker_without_mode_prompt(monkeypatch):
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
        customer.common,
        "_checkbox_prompt",
        lambda prompt, choices, **kwargs: (
            captured.setdefault("prompt", prompt),
            captured.setdefault("values", [choice.value for choice in choices]),
            None,
        )[-1],
    )

    def fake_select(*_args, **_kwargs):
        select_calls["count"] += 1
        return None

    monkeypatch.setattr(customer.common, "_select_prompt", fake_select)

    customer.run_customer_report()

    assert "Pilih Customer" in captured["prompt"]
    assert captured["values"] == ["alpha", "bravo"]
    assert select_calls["count"] == 0


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

    monkeypatch.setattr("backend.config.loader.list_customers", lambda: customers)
    monkeypatch.setattr(
        "backend.config.loader.load_customer_config",
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


def test_run_customer_report_returns_false_when_cancelled_from_picker(monkeypatch):
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
        customer.common,
        "_checkbox_prompt",
        lambda _msg, _choices, **_kw: None,
    )

    result = customer.run_customer_report()

    assert result is False


def test_run_customer_report_single_selection_runs_detail_flow(monkeypatch):
    customers = [
        {
            "customer_id": "alpha",
            "display_name": "Alpha",
            "account_count": 1,
            "checks": ["health"],
            "slack_enabled": False,
        },
    ]

    monkeypatch.setattr(customer, "print_mini_banner", lambda: None)
    monkeypatch.setattr(customer, "print_section_header", lambda *a, **kw: None)
    monkeypatch.setattr(customer, "_render_customer_dashboard", lambda *a: None)
    monkeypatch.setattr(customer, "list_customers", lambda: customers)
    monkeypatch.setattr(
        customer.common,
        "_checkbox_prompt",
        lambda _msg, _choices, **_kw: ["alpha"],
    )
    monkeypatch.setattr(
        customer,
        "load_customer_config",
        lambda customer_id: {
            "customer_id": customer_id,
            "display_name": "Alpha",
            "accounts": [{"profile": "prod-a", "region": "ap-southeast-3"}],
            "checks": ["health"],
        },
    )

    flow_calls = {"detail": 0, "auto": 0, "slack": 0}
    monkeypatch.setattr(customer, "_run_generic_customer", lambda _cfg: {"ok": True})
    monkeypatch.setattr(
        customer,
        "_run_generic_customer",
        lambda _cfg: (
            flow_calls.__setitem__("detail", flow_calls["detail"] + 1) or {"ok": True}
        ),
    )
    monkeypatch.setattr(
        customer,
        "_run_customer_auto",
        lambda _cfg: flow_calls.__setitem__("auto", flow_calls["auto"] + 1),
    )
    monkeypatch.setattr(
        customer,
        "_prompt_slack",
        lambda _cfg: flow_calls.__setitem__("slack", flow_calls["slack"] + 1),
    )

    result = customer.run_customer_report()

    assert result is True
    assert flow_calls["detail"] == 1
    assert flow_calls["auto"] == 0
    assert flow_calls["slack"] == 1


def test_run_customer_report_retries_when_detail_flow_returns_none(monkeypatch):
    customers = [
        {
            "customer_id": "alpha",
            "display_name": "Alpha",
            "account_count": 1,
            "checks": ["health"],
            "slack_enabled": False,
        },
    ]

    monkeypatch.setattr(customer, "print_mini_banner", lambda: None)
    monkeypatch.setattr(customer, "print_section_header", lambda *a, **kw: None)
    monkeypatch.setattr(customer, "_render_customer_dashboard", lambda *a: None)
    monkeypatch.setattr(customer, "list_customers", lambda: customers)

    selected_seq = iter([["alpha"], None])
    monkeypatch.setattr(
        customer.common,
        "_checkbox_prompt",
        lambda _msg, _choices, **_kw: next(selected_seq),
    )

    monkeypatch.setattr(
        customer,
        "load_customer_config",
        lambda customer_id: {
            "customer_id": customer_id,
            "display_name": "Alpha",
            "accounts": [{"profile": "prod-a", "region": "ap-southeast-3"}],
            "checks": ["health"],
        },
    )

    detail_calls = {"count": 0}

    def fake_detail(_cfg):
        detail_calls["count"] += 1
        return None

    monkeypatch.setattr(customer, "_run_generic_customer", fake_detail)

    result = customer.run_customer_report()

    assert detail_calls["count"] == 1
    assert result is False


def test_run_customer_report_multi_selection_runs_auto(monkeypatch):
    customers = [
        {
            "customer_id": "alpha",
            "display_name": "Alpha",
            "account_count": 1,
            "checks": ["health"],
            "slack_enabled": False,
        },
        {
            "customer_id": "bravo",
            "display_name": "Bravo",
            "account_count": 1,
            "checks": ["health"],
            "slack_enabled": False,
        },
    ]

    monkeypatch.setattr(customer, "print_mini_banner", lambda: None)
    monkeypatch.setattr(customer, "print_section_header", lambda *a, **kw: None)
    monkeypatch.setattr(customer, "_render_customer_dashboard", lambda *a: None)
    monkeypatch.setattr(customer, "list_customers", lambda: customers)
    monkeypatch.setattr(
        customer.common,
        "_checkbox_prompt",
        lambda _msg, _choices, **_kw: ["alpha", "bravo"],
    )
    monkeypatch.setattr(
        customer,
        "load_customer_config",
        lambda customer_id: {
            "customer_id": customer_id,
            "display_name": customer_id,
            "accounts": [
                {"profile": f"{customer_id}-prod", "region": "ap-southeast-3"}
            ],
            "checks": ["health"],
        },
    )

    flow_calls = {"detail": 0, "auto": 0}
    monkeypatch.setattr(
        customer,
        "_run_generic_customer",
        lambda _cfg: flow_calls.__setitem__("detail", flow_calls["detail"] + 1),
    )
    monkeypatch.setattr(
        customer,
        "_run_customer_auto",
        lambda _cfg: flow_calls.__setitem__("auto", flow_calls["auto"] + 1),
    )

    result = customer.run_customer_report()

    assert result is True
    assert flow_calls["detail"] == 0
    assert flow_calls["auto"] == 2
