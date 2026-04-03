"""Customer management service with AWS profile detection."""

from __future__ import annotations

import logging
from configparser import ConfigParser
from pathlib import Path

from backend.infra.cloud.aws.clients import get_session as get_aws_session
from backend.utils.crypto import encrypt_secret, decrypt_secret

logger = logging.getLogger(__name__)

AWS_CONFIG_PATH = Path.home() / ".aws" / "config"


def detect_aws_profiles(aws_config_file: str | None = None) -> list[str]:
    """Parse ~/.aws/config and return all profile names."""
    profiles = []
    config_path = Path(aws_config_file) if aws_config_file else AWS_CONFIG_PATH
    try:
        # Use boto3's built-in profile detection
        session = get_aws_session(aws_config_file=aws_config_file)
        profiles = list(session.available_profiles)
    except Exception:
        # Fallback: parse config file directly
        if config_path.exists():
            parser = ConfigParser()
            parser.read(str(config_path))
            for section in parser.sections():
                name = section.replace("profile ", "")
                if name != "default":
                    profiles.append(name)
    return sorted(profiles)


def detect_account_id(
    profile_name: str, aws_config_file: str | None = None
) -> str | None:
    """Try to get AWS account ID for a profile via STS."""
    try:
        session = get_aws_session(
            profile_name=profile_name,
            aws_config_file=aws_config_file,
        )
        sts = session.client("sts")
        identity = sts.get_caller_identity()
        return identity.get("Account")
    except Exception as exc:
        logger.warning(f"Could not detect account ID for {profile_name}: {exc}")
        return None


class CustomerService:
    """Business logic for customer and account management."""

    def __init__(self, customer_repo, aws_config_file: str | None = None):
        self.repo = customer_repo
        self.aws_config_file = aws_config_file

    def list_customers(self) -> list[dict]:
        """Return all customers with their accounts."""
        customers = self.repo.list_customers()
        return [self._serialize_customer(c) for c in customers]

    def get_customer(self, customer_id: str) -> dict | None:
        customer = self.repo.get_customer(customer_id)
        if customer is None:
            return None
        return self._serialize_customer(customer)

    def create_customer(
        self,
        name: str,
        display_name: str,
        checks: list[str] | None = None,
        slack_webhook_url: str | None = None,
        slack_channel: str | None = None,
        slack_enabled: bool = False,
        sso_session: str | None = None,
        report_mode: str = "summary",
        label: str | None = None,
    ) -> dict:
        existing = self.repo.get_customer_by_name(name)
        if existing:
            raise ValueError(f"Customer with name '{name}' already exists")

        customer = self.repo.create_customer(
            name=name,
            display_name=display_name,
            checks=checks or [],
            slack_webhook_url=slack_webhook_url,
            slack_channel=slack_channel,
            slack_enabled=slack_enabled,
            sso_session=sso_session,
            report_mode=report_mode,
            label=label,
        )
        self.repo.commit()
        return self._serialize_customer(customer)

    def update_customer(self, customer_id: str, **kwargs) -> dict | None:
        customer = self.repo.update_customer(customer_id, **kwargs)
        if customer is None:
            return None
        self.repo.commit()
        return self._serialize_customer(customer)

    def delete_customer(self, customer_id: str) -> bool:
        result = self.repo.delete_customer(customer_id)
        if result:
            self.repo.commit()
        return result

    def add_account(
        self,
        customer_id: str,
        profile_name: str,
        display_name: str,
        config_extra: dict | None = None,
        region: str | None = None,
        alarm_names: list[str] | None = None,
        auth_method: str = "profile",
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        role_arn: str | None = None,
        external_id: str | None = None,
        app_secret: str | None = None,
    ) -> dict:
        # Auto-detect AWS account ID (only meaningful for profile auth)
        account_id = (
            detect_account_id(profile_name, self.aws_config_file)
            if auth_method == "profile"
            else None
        )

        # Encrypt secret key if provided
        secret_enc = None
        if aws_secret_access_key and app_secret:
            secret_enc = encrypt_secret(aws_secret_access_key, app_secret)

        account = self.repo.add_account(
            customer_id=customer_id,
            profile_name=profile_name,
            display_name=display_name,
            account_id=account_id,
            config_extra=config_extra,
            region=region,
            alarm_names=alarm_names,
            auth_method=auth_method,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key_enc=secret_enc,
            role_arn=role_arn,
            external_id=external_id,
        )
        self.repo.commit()
        return self._serialize_account(account)

    def update_account(
        self,
        account_id: str,
        app_secret: str | None = None,
        **kwargs,
    ) -> dict | None:
        # Handle secret encryption before delegating to repo
        raw_secret = kwargs.pop("aws_secret_access_key", None)
        if raw_secret is not None and app_secret:
            kwargs["aws_secret_access_key_enc"] = encrypt_secret(raw_secret, app_secret)

        account = self.repo.update_account(account_id, **kwargs)
        if account is None:
            return None
        self.repo.commit()
        return self._serialize_account(account)

    def delete_account(self, account_id: str) -> bool:
        result = self.repo.delete_account(account_id)
        if result:
            self.repo.commit()
        return result

    def discover_account_alarms(self, account_id: str) -> list[str]:
        """Discover CloudWatch alarm names for an account and save them to DB."""
        from backend.domain.services.check_executor import _build_creds_for_account

        account = self.repo.get_account(account_id)
        if account is None:
            raise ValueError("Account not found")

        creds = _build_creds_for_account(account, aws_config_file=self.aws_config_file)
        if creds is None:
            session = get_aws_session(
                profile_name=account.profile_name,
                aws_config_file=self.aws_config_file,
            )
        else:
            session = get_aws_session(
                aws_access_key_id=creds["aws_access_key_id"],
                aws_secret_access_key=creds["aws_secret_access_key"],
                aws_session_token=creds.get("aws_session_token"),
                aws_config_file=self.aws_config_file,
            )
        cw = session.client("cloudwatch")

        paginator = cw.get_paginator("describe_alarms")
        alarm_names: list[str] = []
        for page in paginator.paginate(AlarmTypes=["MetricAlarm", "CompositeAlarm"]):
            for alarm in page.get("MetricAlarms", []):
                alarm_names.append(alarm["AlarmName"])
            for alarm in page.get("CompositeAlarms", []):
                alarm_names.append(alarm["AlarmName"])

        alarm_names.sort()

        self.repo.update_account(account_id, alarm_names=alarm_names)
        self.repo.commit()
        return alarm_names

    def discover_account_full(self, account_id: str) -> dict:
        """Discover AWS account ID, alarms, EC2 instances, and RDS resources. Saves to DB."""
        from backend.domain.services.check_executor import _build_creds_for_account

        account = self.repo.get_account(account_id)
        if account is None:
            raise ValueError("Account not found")

        creds = _build_creds_for_account(account, aws_config_file=self.aws_config_file)
        if creds is None:
            session = get_aws_session(
                profile_name=account.profile_name,
                aws_config_file=self.aws_config_file,
            )
        else:
            session = get_aws_session(
                aws_access_key_id=creds["aws_access_key_id"],
                aws_secret_access_key=creds["aws_secret_access_key"],
                aws_session_token=creds.get("aws_session_token"),
                aws_config_file=self.aws_config_file,
            )

        result = {
            "aws_account_id": None,
            "alarm_names": [],
            "ec2_instances": [],
            "rds_clusters": [],
            "rds_instances": [],
            "errors": [],
        }

        # 1. STS — get AWS account ID
        try:
            sts = session.client("sts")
            identity = sts.get_caller_identity()
            result["aws_account_id"] = identity.get("Account")
        except Exception as e:
            result["errors"].append(f"STS: {e}")

        # 2. CloudWatch — discover alarms (use account region if set, else default)
        region = account.region or "ap-southeast-3"
        try:
            cw = session.client("cloudwatch", region_name=region)
            paginator = cw.get_paginator("describe_alarms")
            alarm_names: list[str] = []
            for page in paginator.paginate(
                AlarmTypes=["MetricAlarm", "CompositeAlarm"]
            ):
                for alarm in page.get("MetricAlarms", []):
                    alarm_names.append(alarm["AlarmName"])
                for alarm in page.get("CompositeAlarms", []):
                    alarm_names.append(alarm["AlarmName"])
            alarm_names.sort()
            result["alarm_names"] = alarm_names
        except Exception as e:
            result["errors"].append(f"CloudWatch: {e}")

        # 3. EC2 — list running instances across all enabled regions
        try:
            ec2_default = session.client("ec2", region_name=region)
            try:
                regions = [
                    r["RegionName"]
                    for r in ec2_default.describe_regions(AllRegions=False).get(
                        "Regions", []
                    )
                    if r.get("RegionName")
                ]
            except Exception:
                regions = [region]

            ec2_instances: list[dict] = []
            seen_ids: set[str] = set()
            for reg in regions:
                try:
                    ec2 = session.client("ec2", region_name=reg)
                    paginator = ec2.get_paginator("describe_instances")
                    for page in paginator.paginate(
                        Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
                    ):
                        for reservation in page.get("Reservations", []):
                            for inst in reservation.get("Instances", []):
                                iid = inst.get("InstanceId")
                                if not iid or iid in seen_ids:
                                    continue
                                seen_ids.add(iid)
                                name = next(
                                    (
                                        t["Value"]
                                        for t in (inst.get("Tags") or [])
                                        if t.get("Key") == "Name"
                                    ),
                                    "-",
                                )
                                ec2_instances.append(
                                    {
                                        "instance_id": iid,
                                        "name": name,
                                        "instance_type": inst.get("InstanceType", "-"),
                                        "region": reg,
                                        "platform": "windows"
                                        if "windows"
                                        in str(
                                            inst.get("Platform")
                                            or inst.get("PlatformDetails")
                                            or ""
                                        ).lower()
                                        else "linux",
                                    }
                                )
                except Exception:
                    continue
            result["ec2_instances"] = ec2_instances
        except Exception as e:
            result["errors"].append(f"EC2: {e}")

        # 4. RDS — clusters and instances
        try:
            rds = session.client("rds", region_name=region)
            try:
                clusters = rds.describe_db_clusters().get("DBClusters", [])
                result["rds_clusters"] = [
                    {
                        "cluster_id": c.get("DBClusterIdentifier"),
                        "engine": c.get("Engine"),
                        "status": c.get("Status"),
                    }
                    for c in clusters
                ]
            except Exception:
                pass
            try:
                instances = rds.describe_db_instances().get("DBInstances", [])
                result["rds_instances"] = [
                    {
                        "instance_id": i.get("DBInstanceIdentifier"),
                        "engine": i.get("Engine"),
                        "instance_class": i.get("DBInstanceClass"),
                        "status": i.get("DBInstanceStatus"),
                        "cluster_id": i.get("DBClusterIdentifier"),
                    }
                    for i in instances
                ]
            except Exception:
                pass
        except Exception as e:
            result["errors"].append(f"RDS: {e}")

        # Save to DB
        from datetime import datetime, timezone as tz

        update_kwargs: dict = {}
        if result["aws_account_id"]:
            update_kwargs["account_id"] = result["aws_account_id"]
        if result["alarm_names"]:
            update_kwargs["alarm_names"] = result["alarm_names"]

        # Persist EC2/RDS snapshot in config_extra["_discovery"]
        existing_extra = dict(account.config_extra or {})
        existing_extra["_discovery"] = {
            "timestamp": datetime.now(tz.utc).isoformat(),
            "ec2_instances": result["ec2_instances"],
            "rds_clusters": result["rds_clusters"],
            "rds_instances": result["rds_instances"],
            "errors": result["errors"],
        }
        update_kwargs["config_extra"] = existing_extra

        self.repo.update_account(account_id, **update_kwargs)
        self.repo.commit()

        return result

    def list_account_check_configs(self, account_id: str) -> list[dict]:
        account = self.repo.get_account(account_id)
        if account is None:
            raise ValueError("Account not found")
        rows = self.repo.list_account_check_configs(account_id)
        return [
            {
                "account_id": row.account_id,
                "check_name": row.check_name,
                "config": row.config,
            }
            for row in rows
        ]

    def set_account_check_config(
        self, account_id: str, check_name: str, config: dict
    ) -> dict:
        account = self.repo.get_account(account_id)
        if account is None:
            raise ValueError("Account not found")

        row = self.repo.upsert_account_check_config(
            account_id=account_id,
            check_name=check_name,
            config=config,
        )
        self.repo.commit()
        return {
            "account_id": row.account_id,
            "check_name": row.check_name,
            "config": row.config,
        }

    def delete_account_check_config(self, account_id: str, check_name: str) -> bool:
        account = self.repo.get_account(account_id)
        if account is None:
            raise ValueError("Account not found")
        deleted = self.repo.delete_account_check_config(account_id, check_name)
        if deleted:
            self.repo.commit()
        return deleted

    def detect_profiles(self) -> dict:
        """Detect AWS profiles and compare with mapped ones."""
        all_profiles = detect_aws_profiles(self.aws_config_file)
        mapped_profiles = self.repo.get_mapped_profiles()
        unmapped = [p for p in all_profiles if p not in mapped_profiles]

        return {
            "all_profiles": all_profiles,
            "mapped_profiles": mapped_profiles,
            "unmapped_profiles": unmapped,
        }

    @staticmethod
    def _yaml_daily_arbel_to_sections(acct: dict) -> list[dict] | None:
        """Build sections list from YAML account config for daily-arbel check."""
        daily = acct.get("daily_arbel")
        if not daily:
            return None

        main_section: dict = {
            "section_name": acct.get("display_name", acct.get("profile", "")),
            "service_type": daily.get("service_type", "rds"),
            "alarm_regions": daily.get("alarm_regions") or [],
            "instances": dict(daily.get("instances") or {}),
            "instance_names": dict(daily.get("instance_names") or {}),
            "metrics": list(daily.get("metrics") or []),
            "thresholds": dict(daily.get("thresholds") or {}),
            "role_thresholds": dict(daily.get("role_thresholds") or {}),
            "alarm_thresholds": dict(daily.get("alarm_thresholds") or {}),
        }
        cluster_id = daily.get("cluster_id")
        if cluster_id:
            main_section["cluster_id"] = cluster_id

        sections = [main_section]

        for extra in acct.get("daily_arbel_extra") or []:
            if isinstance(extra, dict):
                sections.append(dict(extra))

        return sections

    def import_from_yaml(self, customer_config: dict) -> dict:
        """Import a customer from YAML config format into database.

        Used for migrating existing YAML configs to DB.
        """
        cid = customer_config.get("customer_id", "")
        display = customer_config.get("display_name", cid)
        slack_cfg = customer_config.get("slack", {})
        checks = customer_config.get("checks", [])
        sso_session = customer_config.get("sso_session")

        # Create or get customer
        existing = self.repo.get_customer_by_name(cid)
        if existing:
            customer = existing
            # Update fields that may have changed
            self.repo.update_customer(
                customer.id,
                checks=checks,
                sso_session=sso_session,
                slack_webhook_url=slack_cfg.get("webhook_url"),
                slack_channel=slack_cfg.get("channel"),
                slack_enabled=bool(slack_cfg.get("enabled", False)),
            )
        else:
            customer = self.repo.create_customer(
                name=cid,
                display_name=display,
                checks=checks,
                sso_session=sso_session,
                slack_webhook_url=slack_cfg.get("webhook_url"),
                slack_channel=slack_cfg.get("channel"),
                slack_enabled=bool(slack_cfg.get("enabled", False)),
            )

        # Add / update accounts
        added = 0
        updated = 0
        for acct in customer_config.get("accounts", []):
            profile = acct.get("profile")
            if not profile:
                continue

            existing_accounts = self.repo.get_accounts_by_customer(
                customer.id, active_only=False
            )
            existing_acct = next(
                (a for a in existing_accounts if a.profile_name == profile), None
            )

            # Extract check-specific config as config_extra
            config_extra = {}
            for key in ("daily_arbel", "daily_budget"):
                if key in acct:
                    config_extra[key] = acct[key]
            # sso: false stored in config_extra too
            if "sso" in acct:
                config_extra["sso"] = acct["sso"]

            alarm_names = acct.get("alarm_names") or None
            region = acct.get("region") or None

            if existing_acct:
                self.repo.update_account(
                    existing_acct.id,
                    display_name=acct.get("display_name", profile),
                    account_id=acct.get("account_id", existing_acct.account_id),
                    config_extra=config_extra
                    if config_extra
                    else existing_acct.config_extra,
                    alarm_names=alarm_names,
                    region=region,
                )
                account_db_id = existing_acct.id
                updated += 1
            else:
                new_acct = self.repo.add_account(
                    customer_id=customer.id,
                    profile_name=profile,
                    display_name=acct.get("display_name", profile),
                    account_id=acct.get("account_id"),
                    config_extra=config_extra if config_extra else None,
                    alarm_names=alarm_names,
                    region=region,
                )
                account_db_id = new_acct.id if new_acct else None
                added += 1

            # Migrate daily-arbel config to AccountCheckConfig table
            if account_db_id:
                sections = self._yaml_daily_arbel_to_sections(acct)
                if sections:
                    self.repo.upsert_account_check_config(
                        account_id=account_db_id,
                        check_name="daily-arbel",
                        config={"sections": sections},
                    )

        self.repo.commit()
        return {
            "customer_id": customer.id,
            "name": customer.name,
            "accounts_added": added,
            "accounts_updated": updated,
        }

    # -- Serialization --

    @staticmethod
    def _serialize_customer(customer) -> dict:
        return {
            "id": customer.id,
            "name": customer.name,
            "display_name": customer.display_name,
            "checks": customer.checks or [],
            "sso_session": customer.sso_session,
            "slack_webhook_url": customer.slack_webhook_url,
            "slack_channel": customer.slack_channel,
            "slack_enabled": customer.slack_enabled,
            "report_mode": customer.report_mode,
            "label": customer.label,
            "created_at": customer.created_at.isoformat(),
            "updated_at": customer.updated_at.isoformat(),
            "accounts": [
                CustomerService._serialize_account(acc) for acc in customer.accounts
            ],
        }

    @staticmethod
    def _serialize_account(account) -> dict:
        return {
            "id": account.id,
            "profile_name": account.profile_name,
            "account_id": account.account_id,
            "display_name": account.display_name,
            "is_active": account.is_active,
            "config_extra": account.config_extra,
            "region": account.region,
            "alarm_names": account.alarm_names,
            "auth_method": getattr(account, "auth_method", "profile") or "profile",
            "aws_access_key_id": getattr(account, "aws_access_key_id", None),
            "role_arn": getattr(account, "role_arn", None),
            "external_id": getattr(account, "external_id", None),
            # aws_secret_access_key_enc is intentionally never returned
            "created_at": account.created_at.isoformat(),
        }
