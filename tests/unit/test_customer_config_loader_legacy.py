from monitoring_hub.customers.loader import load_customer_config, find_customer_account


def test_load_customer_config_reads_aryanoble_yaml():
    cfg = load_customer_config("aryanoble")

    assert cfg["customer_id"] == "aryanoble"
    assert "accounts" in cfg
    assert any(a["account_id"] == "620463044477" for a in cfg["accounts"])


def test_find_customer_account_by_account_id():
    account = find_customer_account("aryanoble", "620463044477")

    assert account is not None
    assert account["display_name"] == "CONNECT Prod (Non CIS)"
    assert "daily_arbel" in account
