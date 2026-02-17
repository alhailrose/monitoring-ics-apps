"""Load customer/account configuration from canonical src config defaults.

During migration this loader falls back to repository `configs/customers/` when
the src defaults are placeholders.
"""

from pathlib import Path

import yaml

from src.configs.schema.validator import validate_customer_config


def _repo_root():
    return Path(__file__).resolve().parents[2]


def _candidate_paths(customer_id):
    root = _repo_root()
    return [
        root / "configs" / "customers" / f"{customer_id}.yaml",
        root / "src" / "configs" / "defaults" / "customers" / f"{customer_id}.yaml",
    ]


def _find_existing_path(customer_id):
    for path in _candidate_paths(customer_id):
        if path.exists():
            return path
    return None


def load_customer_config(customer_id):
    path = _find_existing_path(customer_id)
    if path is None:
        raise FileNotFoundError(f"customer config not found for: {customer_id}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    if raw.get("source_file"):
        source_path = _repo_root() / str(raw["source_file"])
        if source_path.exists():
            with open(source_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}

    return validate_customer_config(raw)


def find_customer_account(customer_id, account_id):
    cfg = load_customer_config(customer_id)
    for item in cfg.get("accounts", []):
        if str(item.get("account_id")) == str(account_id):
            return item
    return None
