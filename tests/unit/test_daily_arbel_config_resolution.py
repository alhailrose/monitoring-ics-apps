from checks.daily_arbel import DailyArbelChecker


def test_resolve_account_config_uses_customer_mapping_by_account_id(monkeypatch):
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=3)

    monkeypatch.setattr(
        "src.checks.aryanoble.daily_arbel.find_customer_account",
        lambda customer_id, account_id: {
            "account_id": account_id,
            "display_name": "Custom Alias",
            "daily_arbel": {
                "instances": {"writer": "my-instance"},
                "metrics": ["CPUUtilization"],
                "thresholds": {"CPUUtilization": 75},
            },
        },
    )

    cfg = checker._resolve_account_config("some-local-profile", "123456789012")

    assert cfg is not None
    assert cfg["account_name"] == "Custom Alias"
    assert cfg["instances"]["writer"] == "my-instance"


def test_resolve_account_config_falls_back_to_legacy_profile_map():
    checker = DailyArbelChecker(region="ap-southeast-3", window_hours=3)

    cfg = checker._resolve_account_config("connect-prod", "620463044477")

    assert cfg is not None
    assert cfg["account_name"] == "CONNECT Prod (Non CIS)"
