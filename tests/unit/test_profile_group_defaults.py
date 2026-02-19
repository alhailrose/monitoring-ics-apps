from src.core.runtime.config_loader import DEFAULT_PROFILE_GROUPS
from src.configs.loader import load_customer_config


def test_aryanoble_default_group_includes_new_backup_accounts():
    aryanoble = DEFAULT_PROFILE_GROUPS["Aryanoble"]

    assert aryanoble["dwh"] == "084056488725"
    assert aryanoble["genero-empower"] == "941377160792"


def test_ffi_default_group_exists_with_single_account():
    ffi_group = DEFAULT_PROFILE_GROUPS["FFI"]

    assert ffi_group == {"ffi": "315897480848"}


def test_aryanoble_customer_config_includes_new_backup_accounts():
    cfg = load_customer_config("aryanoble")
    profiles = {account["profile"]: account for account in cfg["accounts"]}

    assert profiles["dwh"]["account_id"] == "084056488725"
    assert profiles["genero-empower"]["account_id"] == "941377160792"
