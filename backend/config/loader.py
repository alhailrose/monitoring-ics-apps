"""Load customer/account configuration from a single canonical source.

Canonical source:
- packaged defaults (`src/configs/defaults/customers`)

Optional override (explicit only):
- `MONITORING_HUB_CONFIG_DIR` -> `<dir>/configs/customers`
"""

from pathlib import Path
from typing import List

import yaml

from backend.config.schema.validator import validate_customer_config


def _repo_root():
    return Path(__file__).resolve().parents[2]


def _module_defaults_dir():
    return Path(__file__).resolve().parent / "defaults" / "customers"


def _legacy_module_defaults_dir():
    return _repo_root() / "src" / "configs" / "defaults" / "customers"


def _repo_configs_dir():
    return _repo_root() / "configs" / "customers"


def _user_config_dir():
    """Return explicit override config directory, if configured.

    We intentionally do not auto-read `~/.monitoring-hub/...` to avoid hidden
    drift between machines. Override is opt-in via env var only.
    """
    import os

    config_home = os.getenv("MONITORING_HUB_CONFIG_DIR")
    if not config_home:
        return None
    return Path(config_home) / "configs" / "customers"


def _dedupe_paths(paths):
    out = []
    seen = set()
    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        out.append(path)
    return out


def _candidate_paths(customer_id):
    override_dir = _user_config_dir()
    candidates = []
    if override_dir is not None:
        candidates.append(override_dir / f"{customer_id}.yaml")
    candidates.append(_module_defaults_dir() / f"{customer_id}.yaml")
    candidates.append(_legacy_module_defaults_dir() / f"{customer_id}.yaml")
    candidates.append(_repo_configs_dir() / f"{customer_id}.yaml")
    return _dedupe_paths(candidates)


def _find_existing_path(customer_id):
    for path in _candidate_paths(customer_id):
        if path.exists():
            return path
    return None


def _resolve_source_file(raw):
    source_file = raw.get("source_file")
    if not source_file:
        return raw

    candidates = _dedupe_paths(
        [
            _repo_root() / str(source_file),
            Path.cwd() / str(source_file),
        ]
    )
    for source_path in candidates:
        if source_path.exists():
            with open(source_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    return raw


def load_customer_config(customer_id):
    path = _find_existing_path(customer_id)
    if path is None:
        raise FileNotFoundError(f"customer config not found for: {customer_id}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    raw = _resolve_source_file(raw)

    return validate_customer_config(raw)


def find_customer_account(customer_id, account_id):
    cfg = load_customer_config(customer_id)
    for item in cfg.get("accounts", []):
        if str(item.get("account_id")) == str(account_id):
            return item
    return None


def get_customer_profiles(
    customer_id: str,
    exclude_pattern: str | None = "master",
) -> list[str]:
    """Get profile names from a customer's YAML config.

    Args:
        customer_id: Customer ID (e.g., 'aryanoble')
        exclude_pattern: Exclude profiles containing this pattern (default: 'master')

    Returns:
        List of profile names from the customer's accounts.
        Returns empty list if customer not found.
    """
    try:
        cfg = load_customer_config(customer_id)
    except FileNotFoundError:
        return []

    profiles = []
    for account in cfg.get("accounts", []):
        profile = account.get("profile")
        if not profile:
            continue
        # Exclude profiles matching pattern (case-insensitive)
        if exclude_pattern and exclude_pattern.lower() in profile.lower():
            continue
        profiles.append(profile)

    return profiles


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
    customers_dirs = []
    override_dir = _user_config_dir()
    if override_dir is not None:
        customers_dirs.append(override_dir)
    customers_dirs.append(_module_defaults_dir())
    customers_dirs.append(_legacy_module_defaults_dir())
    customers_dirs.append(_repo_configs_dir())
    customers_dirs = _dedupe_paths(customers_dirs)
    results = []

    seen_ids = set()
    for customers_dir in customers_dirs:
        if not customers_dir.exists():
            continue
        for yaml_path in sorted(customers_dir.glob("*.yaml")):
            customer_id = yaml_path.stem
            if customer_id in seen_ids:
                continue
            seen_ids.add(customer_id)
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    raw = yaml.safe_load(f) or {}

                # Follow source_file redirect if present
                raw = _resolve_source_file(raw)

                results.append(
                    {
                        "customer_id": raw.get("customer_id", yaml_path.stem),
                        "display_name": raw.get("display_name", yaml_path.stem),
                        "path": str(yaml_path),
                        "account_count": len(raw.get("accounts", [])),
                        "checks": raw.get("checks", []),
                        "slack_enabled": bool(
                            raw.get("slack", {}).get("enabled", False)
                            and raw.get("slack", {}).get("webhook_url")
                        ),
                    }
                )
            except Exception:
                results.append(
                    {
                        "customer_id": yaml_path.stem,
                        "display_name": yaml_path.stem,
                        "path": str(yaml_path),
                        "account_count": 0,
                        "checks": [],
                        "slack_enabled": False,
                        "error": "failed to parse",
                    }
                )

    return results


def get_alarm_names_for_profile(profile: str) -> list:
    """Return flat alarm_names list for a given AWS profile name.

    Scans all customer YAML configs to find the account matching
    the profile name, then returns its alarm_names list (or [] if not set).
    """
    for customer in list_customers():
        try:
            cfg = load_customer_config(customer["customer_id"])
            for account in cfg.get("accounts", []):
                if account.get("profile") == profile:
                    return account.get("alarm_names", [])
        except Exception:
            continue
    return []


def collect_customer_profiles(sso_session: str | None = None) -> list[str]:
    """Collect AWS profiles from customer configs.

    Args:
        sso_session: Optional filter by customer-level sso_session.

    Returns:
        Ordered unique list of profile names.
    """
    profiles: list[str] = []
    seen: set[str] = set()

    for customer in list_customers():
        customer_id = customer.get("customer_id")
        if not customer_id:
            continue

        try:
            cfg = load_customer_config(customer_id)
        except Exception:
            continue

        if sso_session is not None and cfg.get("sso_session") != sso_session:
            continue

        for account in cfg.get("accounts", []):
            profile = account.get("profile")
            if not profile or profile in seen:
                continue
            seen.add(profile)
            profiles.append(profile)

    return profiles


def get_profile_metadata(profile: str) -> dict:
    """Return account metadata from customer YAML for a profile.

    Returns keys:
    - profile
    - customer_id
    - customer_display_name
    - account_id
    - display_name (account display name)
    """
    target_profile = str(profile or "")
    target_lower = target_profile.lower()

    for customer in list_customers():
        customer_id = customer.get("customer_id")
        if not customer_id:
            continue
        try:
            cfg = load_customer_config(customer_id)
        except Exception:
            continue

        customer_display = cfg.get("display_name") or customer_id
        for account in cfg.get("accounts", []):
            account_profile = str(account.get("profile") or "")
            if (
                account_profile != target_profile
                and account_profile.lower() != target_lower
            ):
                continue
            return {
                "profile": account_profile or target_profile,
                "customer_id": customer_id,
                "customer_display_name": customer_display,
                "account_id": str(account.get("account_id") or "Unknown"),
                "display_name": account.get("display_name")
                or customer_display
                or account_profile
                or target_profile,
            }

    return {
        "profile": target_profile,
        "customer_id": None,
        "customer_display_name": None,
        "account_id": "Unknown",
        "display_name": target_profile,
    }
