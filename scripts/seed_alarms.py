"""Seed alarm_names into config_extra for Aryanoble accounts.

Populates alarm_verification.alarm_names in config_extra for each
Aryanoble account that has CloudWatch alarms.

Usage: python -m scripts.seed_alarms
"""

import os

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://monitor:monitor@localhost:5432/monitoring",
)

from backend.infra.database.session import build_session_factory
from backend.infra.database.repositories.customer_repository import CustomerRepository

DATABASE_URL = os.environ["DATABASE_URL"]

# Alarm names per Aryanoble profile, from AWS CLI listing
ALARM_DATA = {
    "connect-prod": [
        "noncis-prod-rds-acu-alarm",
        "noncis-prod-rds-cpu-alarm",
        "noncis-prod-rds-databaseconnections-cluster-alarm",
        "noncis-prod-rds-freeable-memory-alarm",
    ],
    "cis-erha": [
        "CIS Aurora Reader - ACU Alarm",
        "CIS Aurora Reader - Connection Alarm",
        "CIS Aurora Reader - IOs Pricing Alarm",
        "CIS Aurora Reader - Memory Alarm",
        "CIS Aurora Writer - ACU Alarm",
        "CIS Aurora Writer - Connection Alarm",
        "CIS Aurora Writer - IOs Pricing Alarm",
        "CIS Aurora Writer - Memory Alarm",
        "CIS RabbitMQ - CPU Alarm",
    ],
    "dermies-max": [
        "dermies-prod-rds-cpu-alarm",
        "dermies-prod-rds-reader-acu-alarm",
        "dermies-prod-rds-reader-connections-alarm",
        "dermies-prod-rds-reader-cpu-alarm",
        "dermies-prod-rds-reader-freeable-memory-alarm",
        "dermies-prod-rds-writer-acu-alarm",
        "dermies-prod-rds-writer-connections-alarm",
        "dermies-prod-rds-writer-cpu-alarm",
        "dermies-prod-rds-writer-freeable-memory-alarm",
    ],
    "erha-buddy": [
        "TargetTracking-erhabuddy-prod-ecs-node-20251105043431137000000023-AlarmHigh-f9043c7d-dd99-4d69-9ed8-0a2af34c1dc0",
        "TargetTracking-erhabuddy-prod-ecs-node-20251105043431137000000023-AlarmLow-f2a8eddf-a12e-4148-90c9-a5d811e3fd49",
    ],
    "public-web": [
        "CPU Utilization RDS (Mysql)",
        "CPU Utilization RDS (Postgre)",
        "FreeableMemory RDS (Mysql)",
        "FreeableMemory RDS (Postgre)",
        "Total Connection RDS (Mysql)",
        "Total Connection RDS (Postgre)",
    ],
    "HRIS": [
        "aryanoble-prod-Ubuntu20.04-openvpn-cpu-above-80",
        "aryanoble-prod-Ubuntu20.04-openvpn-disk-above-80",
        "aryanoble-prod-Ubuntu20.04-openvpn-mem-above-80",
        "aryanoble-prod-Window2019Base-webserver-cpu-above-80",
        "aryanoble-prod-Window2019Base-webserver Disk C < 10%",
        "aryanoble-prod-Window2019Base-webserver Disk C < 20%",
        "aryanoble-prod-Window2019Base-webserver Disk D < 10%",
        "aryanoble-prod-Window2019Base-webserver Disk D < 20%",
        "aryanoble-prod-Window2019Base-webserver-mem-above-80",
        "aryanoble-prod-Windows2019+SQL2019Standard-database-cpu-above-80",
        "aryanoble-prod-Windows2019+SQL2019Standard-database-disk-above-80",
        "aryanoble-prod-Windows2019+SQL2019Standard-database-disk-D-above-80",
        "aryanoble-prod-Windows2019+SQL2019Standard-database-disk-E-above-80",
        "aryanoble-prod-Windows2019+SQL2019Standard-database-disk-F-above-80",
        "aryanoble-prod-Windows2019+SQL2019Standard-database-disk-G-above-80",
        "aryanoble-prod-Windows2019+SQL2019Standard-database-mem-above-80",
    ],
    "sfa": [
        "sfa-production-openvpn-cpu-above-70",
        "sfa-production-openvpn-disk-above-70",
        "sfa-production-openvpn-mem-above-70",
        "sfa-production-openvpn-new-cpu-above-70",
        "sfa-production-openvpn-new-disk-above-70",
        "sfa-production-openvpn-newm-above-70",
        "vm-database-cpu-above-70",
        "vm-database-disk-C:-below-30",
        "vm-database-mem-above-70",
        "vm-dms-cpu-above-70",
        "vm-dms-disk-C:-below-30",
        "vm-dms-mem-above-70",
        "vm-jobs-cpu-above-70",
        "vm-jobs-disk-above-70",
        "vm-jobs-mem-above-70",
        "vm-sfa-cpu-above-70",
        "vm-sfa-disk-above-70",
        "vm-sfa-mem-above-70",
    ],
    "iris-prod": [
        "rnd-formulation-production-appserver-cpu-above-70",
        "rnd-formulation-production-appserver-disk-above-70",
        "rnd-formulation-production-appserver-mem-above-70",
        "rnd-formulation-production-openvpn-cpu-above-70",
        "rnd-formulation-production-openvpn-disk-above-70",
        "rnd-formulation-production-openvpn-mem-above-70",
        "rnd-formulation-production-rds-cpu-above-70",
        "rnd-formulation-production-rds-disk < 20Gb",
        "rnd-formulation-production-rds-memory < 8Gb",
    ],
    "fee-doctor": [
        "feedoctor-production-backend-checkfailed-alarm",
        "feedoctor-production-backend-cpu-above-70",
        "feedoctor-production-backend-disk-above-70",
        "feedoctor-production-backend-mem-above-70",
        "feedoctor-production-frontend-checkfailed-alarm",
        "feedoctor-production-frontend-cpu-above-70",
        "feedoctor-production-frontend-disk-above-70",
        "feedoctor-production-frontend-mem-above-70",
        "feedoctor-production-openvpn-checkfailed-alarm",
        "feedoctor-production-openvpn-cpu-above-70",
        "feedoctor-production-openvpn-disk-above-70",
        "feedoctor-production-openvpn-mem-above-70",
        "feedoctor-production-rds-cpu-above-70",
        "feedoctor-production-rds-disk < 20Gb",
        "feedoctor-production-rds-mem < 2GB",
    ],
    "tgw": [
        "Alarm for OpenSearch Prod Storage",
        "Second VPN Tunnel State",
        "VPN Tunnel State",
    ],
    "backup-hris": [
        "Disk C Free Space is Below 20%",
        "Disk D Free Space Below 20%",
        "Disk E Free Space Below 20%",
        "Disk F Free Space Below 20%",
        "Disk G Free Space Below 20%",
    ],
    "dwh": [
        "dc-dwh-db-cpu-above-70",
        "dc-dwh-db-disk :C-above-80",
        "dc-dwh-db-disk :D-above-80",
        "dc-dwh-db-memory-above-70",
        "dc-dwh-olap-cpu-above-70",
        "dc-dwh-olap-disk:C-above-80",
        "dc-dwh-olap-memory-above-70",
    ],
    "iris-dev": [
        "rnd-formulation-dev-appserver-cpu-above-70",
        "rnd-formulation-dev-appserver-disk-above-70",
        "rnd-formulation-dev-appserver-mem-above-70",
        "rnd-formulation-dev-database-cpu-above-70",
        "rnd-formulation-dev-database-disk-above-70",
        "rnd-formulation-dev-database-mem-above-70",
        "rnd-formulation-devcpu-above-70",
        "rnd-formulation-dev-openvpn-disk-above-70",
        "rnd-formulation-dev-openvpn-mem-above-70",
    ],
}


def main():
    print("Seeding alarm_names into Aryanoble account config_extra ...")
    session_factory = build_session_factory(DATABASE_URL)

    with session_factory() as session:
        repo = CustomerRepository(session)
        customer = repo.get_customer_by_name("aryanoble")
        if not customer:
            print("  [!] Aryanoble customer not found")
            return

        accounts = repo.get_accounts_by_customer(customer.id, active_only=False)
        account_map = {a.profile_name: a for a in accounts}

        updated = 0
        for profile_name, alarm_names in ALARM_DATA.items():
            acct = account_map.get(profile_name)
            if not acct:
                print(f"  [!] Account not found: {profile_name}")
                continue

            config_extra = dict(acct.config_extra or {})
            config_extra["alarm_verification"] = {"alarm_names": alarm_names}
            repo.update_account(acct.id, config_extra=config_extra)
            print(f"  [+] {profile_name}: {len(alarm_names)} alarms")
            updated += 1

        session.commit()
        print(f"\nDone. Updated {updated} accounts.")


if __name__ == "__main__":
    main()
