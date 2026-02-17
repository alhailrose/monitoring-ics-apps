from src.configs.loader import find_customer_account, load_customer_config

from monitoring_hub.customers.loader import (
    find_customer_account as legacy_find_customer_account,
)
from monitoring_hub.customers.loader import (
    load_customer_config as legacy_load_customer_config,
)


def test_src_loader_reads_aryanoble_config():
    cfg = load_customer_config("aryanoble")

    assert cfg["customer_id"] == "aryanoble"
    assert cfg["accounts"]


def test_legacy_loader_reexports_src_loader():
    assert legacy_load_customer_config is load_customer_config
    assert legacy_find_customer_account is find_customer_account
