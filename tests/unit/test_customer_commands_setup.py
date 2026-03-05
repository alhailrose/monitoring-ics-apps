import pytest
from pathlib import Path

from src.app.cli.customer_commands import (
    classify_profiles_by_mapping,
    customer_assign,
    ensure_profile_assignment_allowed,
    sanitize_checks,
    upsert_customer_account,
)


def test_classify_profiles_by_mapping_returns_mapped_unmapped():
    all_profiles = ["prod-a", "prod-b", "prod-c"]
    customers = [
        {
            "customer_id": "acme",
            "accounts": [
                {"profile": "prod-a", "account_id": "111111111111"},
            ],
        }
    ]

    result = classify_profiles_by_mapping(all_profiles, customers)

    assert result["mapped"] == ["prod-a"]
    assert result["unmapped"] == ["prod-b", "prod-c"]


def test_assign_profile_appends_account_to_customer_yaml():
    customer_cfg = {
        "customer_id": "acme",
        "accounts": [
            {"profile": "prod-a", "account_id": "111111111111"},
        ],
    }

    updated = upsert_customer_account(
        customer_cfg,
        profile="prod-b",
        account_id="222222222222",
        account_name="Prod B",
    )

    assert updated["accounts"] == [
        {"profile": "prod-a", "account_id": "111111111111"},
        {
            "profile": "prod-b",
            "account_id": "222222222222",
            "account_name": "Prod B",
        },
    ]


def test_assign_profile_updates_existing_account_by_profile():
    customer_cfg = {
        "customer_id": "acme",
        "accounts": [
            {
                "profile": "prod-a",
                "account_id": "111111111111",
                "account_name": "Old Name",
            },
        ],
    }

    updated = upsert_customer_account(
        customer_cfg,
        profile="prod-a",
        account_id="999999999999",
        account_name="New Name",
    )

    assert updated["accounts"] == [
        {
            "profile": "prod-a",
            "account_id": "999999999999",
            "account_name": "New Name",
        }
    ]


def test_assign_profile_blocks_duplicate_mapping_without_override():
    customers = [
        {
            "customer_id": "acme",
            "accounts": [
                {"profile": "prod-a", "account_id": "111111111111"},
            ],
        },
        {
            "customer_id": "globex",
            "accounts": [
                {"profile": "prod-b", "account_id": "222222222222"},
            ],
        },
    ]

    with pytest.raises(
        ValueError,
        match="already assigned to customer 'acme'",
    ):
        ensure_profile_assignment_allowed(
            "prod-a",
            customers,
            target_customer_id="globex",
            override=False,
        )


def test_set_checks_persists_only_available_checks():
    selected_checks = ["health", "  cost  ", "invalid-check", "health"]

    sanitized = sanitize_checks(selected_checks)

    assert sanitized == ["health", "cost"]


def test_helpers_handle_accounts_none():
    all_profiles = ["prod-a", "prod-b"]
    customers = [
        {"customer_id": "acme", "accounts": None},
        {
            "customer_id": "globex",
            "accounts": [{"profile": "prod-b", "account_id": "222222222222"}],
        },
    ]

    classification = classify_profiles_by_mapping(all_profiles, customers)

    assert classification == {"mapped": ["prod-b"], "unmapped": ["prod-a"]}
    ensure_profile_assignment_allowed(
        profile="prod-a",
        customers=customers,
        target_customer_id="globex",
        override=False,
    )


def test_customer_assign_blocks_when_some_customer_configs_fail_to_load(monkeypatch):
    target_cfg = {"customer_id": "globex", "accounts": []}
    monkeypatch.setattr(
        "src.app.cli.customer_commands._load_customer_yaml",
        lambda _cid: (Path("/tmp/globex.yaml"), target_cfg),
    )
    monkeypatch.setattr(
        "src.app.cli.customer_commands._load_customer_configs_with_errors",
        lambda: ([{"customer_id": "globex", "accounts": []}], ["acme: failed to parse"]),
    )

    saved = {"called": False}
    monkeypatch.setattr(
        "src.app.cli.customer_commands._save_customer_yaml",
        lambda _path, _cfg: saved.__setitem__("called", True),
    )

    ok = customer_assign("globex")

    assert ok is False
    assert saved["called"] is False


def test_customer_assign_skips_unknown_account_id_when_not_confirmed(monkeypatch):
    target_cfg = {"customer_id": "globex", "accounts": []}
    monkeypatch.setattr(
        "src.app.cli.customer_commands._load_customer_yaml",
        lambda _cid: (Path("/tmp/globex.yaml"), target_cfg),
    )
    monkeypatch.setattr(
        "src.app.cli.customer_commands._load_customer_configs_with_errors",
        lambda: ([{"customer_id": "globex", "accounts": []}], []),
    )
    monkeypatch.setattr("src.app.cli.customer_commands.list_local_profiles", lambda: ["prod-x"])
    monkeypatch.setattr("src.app.cli.customer_commands._select_many", lambda *_args, **_kwargs: ["prod-x"])
    monkeypatch.setattr("src.app.cli.customer_commands._detect_account_id", lambda _profile: "Unknown")
    monkeypatch.setattr("src.app.cli.customer_commands._confirm", lambda *_args, **_kwargs: False)

    saved = {"called": False}
    monkeypatch.setattr(
        "src.app.cli.customer_commands._save_customer_yaml",
        lambda _path, _cfg: saved.__setitem__("called", True),
    )

    ok = customer_assign("globex")

    assert ok is False
    assert target_cfg["accounts"] == []
    assert saved["called"] is False


def test_customer_assign_allows_unknown_account_id_with_confirmation(monkeypatch):
    target_cfg = {"customer_id": "globex", "accounts": []}
    monkeypatch.setattr(
        "src.app.cli.customer_commands._load_customer_yaml",
        lambda _cid: (Path("/tmp/globex.yaml"), target_cfg),
    )
    monkeypatch.setattr(
        "src.app.cli.customer_commands._load_customer_configs_with_errors",
        lambda: ([{"customer_id": "globex", "accounts": []}], []),
    )
    monkeypatch.setattr("src.app.cli.customer_commands.list_local_profiles", lambda: ["prod-x"])
    monkeypatch.setattr("src.app.cli.customer_commands._select_many", lambda *_args, **_kwargs: ["prod-x"])
    monkeypatch.setattr("src.app.cli.customer_commands._detect_account_id", lambda _profile: "Unknown")
    monkeypatch.setattr("src.app.cli.customer_commands._confirm", lambda *_args, **_kwargs: True)

    saved = {"called": False}
    monkeypatch.setattr(
        "src.app.cli.customer_commands._save_customer_yaml",
        lambda _path, _cfg: saved.__setitem__("called", True),
    )

    ok = customer_assign("globex")

    assert ok is True
    assert target_cfg["accounts"] == [{"profile": "prod-x", "account_id": "Unknown"}]
    assert saved["called"] is True
