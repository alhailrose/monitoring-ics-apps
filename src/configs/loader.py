"""Load customer/account configuration from canonical src config defaults.

During migration this loader falls back to repository `configs/customers/` when
the src defaults are placeholders.
"""

from pathlib import Path
from typing import List

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


def find_customer_by_profile(profile: str) -> dict | None:
    """Find which customer owns a given AWS profile.

    Scans all customer YAML configs and returns the customer config
    dict if the profile is found in any customer's accounts list.
    Returns None if no customer owns this profile.
    """
    for customer in list_customers():
        try:
            cfg = load_customer_config(customer["customer_id"])
            for account in cfg.get("accounts", []):
                if account.get("profile") == profile:
                    return cfg
        except Exception:
            continue
    return None


def list_customers() -> List[dict]:
    """Return list of all customer configs found in configs/customers/.

    Each entry has keys: customer_id, display_name, path, account_count.
    """
    root = _repo_root()
    customers_dir = root / "configs" / "customers"
    results = []

    if not customers_dir.exists():
        return results

    for yaml_path in sorted(customers_dir.glob("*.yaml")):
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}

            # Follow source_file redirect if present
            if raw.get("source_file"):
                source_path = root / str(raw["source_file"])
                if source_path.exists():
                    with open(source_path, "r", encoding="utf-8") as f:
                        raw = yaml.safe_load(f) or {}

            results.append({
                "customer_id": raw.get("customer_id", yaml_path.stem),
                "display_name": raw.get("display_name", yaml_path.stem),
                "path": str(yaml_path),
                "account_count": len(raw.get("accounts", [])),
                "checks": raw.get("checks", []),
                "slack_enabled": bool(
                    raw.get("slack", {}).get("enabled", False)
                    and raw.get("slack", {}).get("webhook_url")
                ),
            })
        except Exception:
            results.append({
                "customer_id": yaml_path.stem,
                "display_name": yaml_path.stem,
                "path": str(yaml_path),
                "account_count": 0,
                "checks": [],
                "slack_enabled": False,
                "error": "failed to parse",
            })

    return results
