"""Customer management service with AWS profile detection."""

from __future__ import annotations

import logging
from configparser import ConfigParser
from pathlib import Path

import boto3

logger = logging.getLogger(__name__)

AWS_CONFIG_PATH = Path.home() / ".aws" / "config"


def detect_aws_profiles() -> list[str]:
    """Parse ~/.aws/config and return all profile names."""
    profiles = []
    try:
        # Use boto3's built-in profile detection
        session = boto3.Session()
        profiles = list(session.available_profiles)
    except Exception:
        # Fallback: parse config file directly
        if AWS_CONFIG_PATH.exists():
            parser = ConfigParser()
            parser.read(str(AWS_CONFIG_PATH))
            for section in parser.sections():
                name = section.replace("profile ", "")
                if name != "default":
                    profiles.append(name)
    return sorted(profiles)


def detect_account_id(profile_name: str) -> str | None:
    """Try to get AWS account ID for a profile via STS."""
    try:
        session = boto3.Session(profile_name=profile_name)
        sts = session.client("sts")
        identity = sts.get_caller_identity()
        return identity.get("Account")
    except Exception as exc:
        logger.warning(f"Could not detect account ID for {profile_name}: {exc}")
        return None


class CustomerService:
    """Business logic for customer and account management."""

    def __init__(self, customer_repo):
        self.repo = customer_repo

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
    ) -> dict:
        # Auto-detect AWS account ID
        account_id = detect_account_id(profile_name)

        account = self.repo.add_account(
            customer_id=customer_id,
            profile_name=profile_name,
            display_name=display_name,
            account_id=account_id,
            config_extra=config_extra,
            region=region,
            alarm_names=alarm_names,
        )
        self.repo.commit()
        return self._serialize_account(account)

    def update_account(self, account_id: str, **kwargs) -> dict | None:
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

    def detect_profiles(self) -> dict:
        """Detect AWS profiles and compare with mapped ones."""
        all_profiles = detect_aws_profiles()
        mapped_profiles = self.repo.get_mapped_profiles()
        unmapped = [p for p in all_profiles if p not in mapped_profiles]

        return {
            "all_profiles": all_profiles,
            "mapped_profiles": mapped_profiles,
            "unmapped_profiles": unmapped,
        }

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

            existing_accounts = self.repo.get_accounts_by_customer(customer.id, active_only=False)
            existing_acct = next((a for a in existing_accounts if a.profile_name == profile), None)

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
                    config_extra=config_extra if config_extra else existing_acct.config_extra,
                    alarm_names=alarm_names,
                    region=region,
                )
                updated += 1
            else:
                self.repo.add_account(
                    customer_id=customer.id,
                    profile_name=profile,
                    display_name=acct.get("display_name", profile),
                    account_id=acct.get("account_id"),
                    config_extra=config_extra if config_extra else None,
                    alarm_names=alarm_names,
                    region=region,
                )
                added += 1

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
            "created_at": customer.created_at.isoformat(),
            "updated_at": customer.updated_at.isoformat(),
            "accounts": [
                CustomerService._serialize_account(acc)
                for acc in customer.accounts
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
            "created_at": account.created_at.isoformat(),
        }
