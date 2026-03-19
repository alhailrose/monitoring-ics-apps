"""Re-import all customer YAML configs into the database.

Reads every YAML file in configs/customers/ and upserts each customer
and its accounts via CustomerService.import_from_yaml().  Populates the
new fields that were previously dropped:

  - Customer.checks
  - Customer.sso_session
  - Account.region
  - Account.alarm_names

Requires the Alembic migration 8444b20562ce to have been applied first.

Usage:
    python -m scripts.reimport_yaml_configs

Environment:
    DATABASE_URL  (default: postgresql+psycopg://monitor:monitor@localhost:5432/monitoring)
"""

import os
import sys

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://monitor:monitor@localhost:5432/monitoring",
)

from backend.infra.database.session import build_session_factory
from backend.infra.database.repositories.customer_repository import CustomerRepository
from backend.domain.services.customer_service import CustomerService
from backend.config.loader import list_customers, load_customer_config


DATABASE_URL = os.environ["DATABASE_URL"]

# Customers to skip (e.g. sandbox — no real DB entries expected)
SKIP_CUSTOMERS = {"sandbox"}


def main() -> None:
    print(f"Re-importing customer YAML configs into DB ({DATABASE_URL}) …\n")

    session_factory = build_session_factory(DATABASE_URL)

    # Discover all YAML configs
    all_customers = list_customers()
    print(f"Found {len(all_customers)} customer config(s) in configs/customers/\n")

    ok = 0
    skipped = 0
    failed = 0

    with session_factory() as session:
        repo = CustomerRepository(session)
        service = CustomerService(repo)

        for entry in all_customers:
            cid = entry["customer_id"]

            if cid in SKIP_CUSTOMERS:
                print(f"  [SKIP] {cid}")
                skipped += 1
                continue

            try:
                config = load_customer_config(cid)
            except FileNotFoundError as exc:
                print(f"  [ERR ] {cid} — config not found: {exc}")
                failed += 1
                continue
            except Exception as exc:
                print(f"  [ERR ] {cid} — failed to load config: {exc}")
                failed += 1
                continue

            try:
                result = service.import_from_yaml(config)
                added = result["accounts_added"]
                updated = result["accounts_updated"]
                print(f"  [OK  ] {cid}  (accounts: +{added} added, ~{updated} updated)")
                ok += 1
            except Exception as exc:
                print(f"  [ERR ] {cid} — import failed: {exc}")
                failed += 1

    print(f"\nDone. {ok} imported, {skipped} skipped, {failed} failed.")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
