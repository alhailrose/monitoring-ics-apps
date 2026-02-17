from src.configs.loader import find_customer_account, load_customer_config


def test_src_loader_reads_aryanoble_config():
    cfg = load_customer_config("aryanoble")

    assert cfg["customer_id"] == "aryanoble"
    assert cfg["accounts"]


def test_src_loader_finds_account_by_id():
    account = find_customer_account("aryanoble", "620463044477")
    assert account is not None
    assert account["display_name"] == "CONNECT Prod (Non CIS)"
