"""Seed database from AWS config comments and YAML configs.

Reads #Customer comments from ~/.aws/config to map profiles to customers.
Excludes sandbox accounts (sandbox, prod-sandbox, sandbox-ms-lebaran, sandbox-ics).

Usage: python -m scripts.seed_database
"""

import os
import yaml
from pathlib import Path

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://monitor:monitor@localhost:5432/monitoring",
)

from backend.infra.database.session import build_session_factory
from backend.infra.database.repositories.customer_repository import CustomerRepository


YAML_PATH = "configs/customers/aryanoble.yaml"
AWS_CONFIG_PATH = Path.home() / ".aws" / "config"
DATABASE_URL = os.environ["DATABASE_URL"]

DEFAULT_CHECKS = ["cost", "guardduty", "cloudwatch", "notifications"]

SKIP_PROFILES = {"sandbox", "prod-sandbox", "sandbox-ms-lebaran", "sandbox-ics"}

CHECKS_OVERRIDE = {
    "aryanoble": [
        "cost",
        "guardduty",
        "cloudwatch",
        "notifications",
        "backup",
        "daily-arbel",
    ],
}

CUSTOMER_NAME_MAP = {
    "diamond": "diamond",
    "techmeister": "techmeister",
    "fresnel": "fresnel",
    "kki": "kki",
    "bintang bali indah": "bbi",
    "edot": "edot",
    "ucoal": "ucoal",
    "programa": "programa",
    "aryanoble": "aryanoble",
    "nabati": "ksni",
    "nikp": "nikp",
    "rumahmedia": "rumahmedia",
    "hungryhub": "hungryhub",
    "agung sedayu": "asg",
    "arista web": "arista-web",
    "frisian flag indonesia": "frisianflag",
}

CUSTOMER_DISPLAY_MAP = {
    "diamond": "Diamond",
    "techmeister": "Techmeister",
    "fresnel": "Fresnel",
    "kki": "KKI",
    "bbi": "Bintang Bali Indah",
    "edot": "eDot",
    "ucoal": "uCoal",
    "programa": "Programa",
    "aryanoble": "Aryanoble",
    "ksni": "KSNI",
    "nikp": "NIKP",
    "rumahmedia": "Rumahmedia",
    "hungryhub": "HungryHub",
    "asg": "Agung Sedayu",
    "arista-web": "Arista Web",
    "frisianflag": "Frisian Flag Indonesia",
}

KSNI_EXTRA_PROFILES = [
    {"profile_name": "q-devpro", "account_id": "528160043048"},
    {"profile_name": "sales-support-pma", "account_id": "734881641265"},
]


def parse_aws_config_customers() -> dict:
    """Parse ~/.aws/config and group profiles by #Customer comments.

    Returns dict: {db_name: {"display_name": str, "profiles": [{"profile_name": str, "account_id": str|None}]}}
    """
    raw = AWS_CONFIG_PATH.read_text()
    lines = raw.splitlines()

    customers: dict = {}
    current_customer_key: str | None = None
    current_profile: str | None = None
    current_account_id: str | None = None

    def flush_profile():
        nonlocal current_profile, current_account_id
        if current_profile and current_customer_key:
            if current_profile not in SKIP_PROFILES:
                customers[current_customer_key]["profiles"].append(
                    {"profile_name": current_profile, "account_id": current_account_id}
                )
        current_profile = None
        current_account_id = None

    for line in lines:
        stripped = line.strip()

        # Detect #Customer comment
        if stripped.lower().startswith("#customer "):
            flush_profile()
            comment_name = stripped[len("#customer ") :].strip().lower()
            db_name = CUSTOMER_NAME_MAP.get(comment_name)
            if db_name:
                display_name = CUSTOMER_DISPLAY_MAP.get(db_name, db_name)
                if db_name not in customers:
                    customers[db_name] = {"display_name": display_name, "profiles": []}
                current_customer_key = db_name
            else:
                current_customer_key = None
            continue

        # Detect profile section header
        if stripped.startswith("[profile ") and stripped.endswith("]"):
            flush_profile()
            current_profile = stripped[len("[profile ") : -1].strip()
            current_account_id = None
            continue

        # Non-profile section resets context
        if stripped.startswith("[") and not stripped.startswith("[profile "):
            flush_profile()
            current_profile = None
            current_customer_key = None
            continue

        # Detect sso_account_id
        if stripped.startswith("sso_account_id") and "=" in stripped:
            current_account_id = stripped.split("=", 1)[1].strip()

    flush_profile()
    return customers


def load_yaml(path: str) -> dict:
    """Load a YAML file, return empty dict if not found."""
    p = Path(path)
    if not p.exists():
        return {}
    with open(p) as f:
        return yaml.safe_load(f) or {}


def upsert_customer(
    repo: CustomerRepository,
    db_name: str,
    display_name: str,
    profiles: list,
    yaml_accounts: list | None = None,
) -> None:
    """Create or update a customer and its accounts in the DB."""
    checks = CHECKS_OVERRIDE.get(db_name, DEFAULT_CHECKS)

    customer = repo.get_customer_by_name(db_name)
    if customer is None:
        customer = repo.create_customer(
            name=db_name,
            display_name=display_name,
            checks=checks,
        )
        print(f"  [+] Created customer: {display_name} ({db_name})")
    else:
        if customer.checks != checks:
            repo.update_customer(customer.id, checks=checks)
        print(f"  [~] Updated customer: {display_name} ({db_name})")

    existing_accounts = {
        a.profile_name: a
        for a in repo.get_accounts_by_customer(customer.id, active_only=False)
    }

    for prof in profiles:
        profile_name = prof["profile_name"]
        account_id = prof.get("account_id")
        config_extra = None

        if yaml_accounts:
            for ya in yaml_accounts:
                if ya.get("profile") == profile_name or ya.get("name") == profile_name:
                    config_extra = {
                        k: v
                        for k, v in ya.items()
                        if k not in ("profile", "name", "account_id")
                    }
                    if not config_extra:
                        config_extra = None
                    break

        if profile_name in existing_accounts:
            acct = existing_accounts[profile_name]
            repo.update_account(
                acct.id, account_id=account_id, config_extra=config_extra
            )
            print(
                f"      [~] Account: {profile_name} ({account_id or 'no account_id'})"
            )
        else:
            repo.add_account(
                customer_id=customer.id,
                profile_name=profile_name,
                display_name=profile_name,
                account_id=account_id,
                config_extra=config_extra,
            )
            print(
                f"      [+] Account: {profile_name} ({account_id or 'no account_id'})"
            )


def main():
    print("Seeding database from ~/.aws/config ...")
    session_factory = build_session_factory(DATABASE_URL)

    with session_factory() as session:
        repo = CustomerRepository(session)

        customers = parse_aws_config_customers()
        print(f"Found {len(customers)} customers in ~/.aws/config\n")

        aryanoble_yaml = load_yaml(YAML_PATH)
        aryanoble_accounts = aryanoble_yaml.get("accounts", [])

        for db_name, info in customers.items():
            display_name = info["display_name"]
            profiles = info["profiles"]
            yaml_accounts = aryanoble_accounts if db_name == "aryanoble" else None
            print(f"Processing: {display_name} ({len(profiles)} profiles)")
            upsert_customer(repo, db_name, display_name, profiles, yaml_accounts)

        # KSNI extra profiles not under #Customer Nabati comment
        print("\nAdding KSNI extra profiles ...")
        ksni = repo.get_customer_by_name("ksni")
        if ksni:
            existing = {
                a.profile_name
                for a in repo.get_accounts_by_customer(ksni.id, active_only=False)
            }
            for ep in KSNI_EXTRA_PROFILES:
                if ep["profile_name"] not in existing:
                    repo.add_account(
                        customer_id=ksni.id,
                        profile_name=ep["profile_name"],
                        display_name=ep["profile_name"],
                        account_id=ep["account_id"],
                    )
                    print(
                        f"  [+] KSNI account: {ep['profile_name']} ({ep['account_id']})"
                    )
                else:
                    print(f"  [~] KSNI account already exists: {ep['profile_name']}")
        else:
            print("  [!] KSNI customer not found — skipping extra profiles")

        session.commit()
        print("\nDone. Database seeded successfully.")


if __name__ == "__main__":
    main()
