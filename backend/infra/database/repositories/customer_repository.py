"""Repository for customer and account persistence."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.infra.database.models import Account, Customer, AccountCheckConfig


class CustomerRepository:
    def __init__(self, session: Session):
        self.session = session

    # -- Customer CRUD --

    def create_customer(
        self,
        name: str,
        display_name: str,
        checks: list[str] | None = None,
        slack_webhook_url: str | None = None,
        slack_channel: str | None = None,
        slack_enabled: bool = False,
        sso_session: str | None = None,
    ) -> Customer:
        customer = Customer(
            name=name,
            display_name=display_name,
            checks=checks or [],
            slack_webhook_url=slack_webhook_url,
            slack_channel=slack_channel,
            slack_enabled=slack_enabled,
            sso_session=sso_session,
        )
        self.session.add(customer)
        self.session.flush()
        self.session.refresh(customer)
        return customer

    def get_customer(self, customer_id: str) -> Customer | None:
        stmt = (
            select(Customer)
            .options(selectinload(Customer.accounts))
            .where(Customer.id == customer_id)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_customer_by_name(self, name: str) -> Customer | None:
        stmt = (
            select(Customer)
            .options(selectinload(Customer.accounts))
            .where(Customer.name == name)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_customers(self) -> list[Customer]:
        stmt = (
            select(Customer)
            .options(selectinload(Customer.accounts))
            .order_by(Customer.display_name)
        )
        return list(self.session.execute(stmt).scalars().all())

    def update_customer(self, customer_id: str, **kwargs) -> Customer | None:
        customer = self.get_customer(customer_id)
        if customer is None:
            return None
        for key, value in kwargs.items():
            if hasattr(customer, key):
                setattr(customer, key, value)
        customer.updated_at = datetime.now(timezone.utc)
        self.session.flush()
        return customer

    def delete_customer(self, customer_id: str) -> bool:
        customer = self.get_customer(customer_id)
        if customer is None:
            return False
        self.session.delete(customer)
        self.session.flush()
        return True

    # -- Account CRUD --

    def add_account(
        self,
        customer_id: str,
        profile_name: str,
        display_name: str,
        account_id: str | None = None,
        config_extra: dict | None = None,
        region: str | None = None,
        alarm_names: list[str] | None = None,
    ) -> Account:
        account = Account(
            customer_id=customer_id,
            profile_name=profile_name,
            display_name=display_name,
            account_id=account_id,
            config_extra=config_extra,
            region=region,
            alarm_names=alarm_names,
        )
        self.session.add(account)
        self.session.flush()
        self.session.refresh(account)
        return account

    def get_account(self, account_id: str) -> Account | None:
        stmt = (
            select(Account)
            .options(selectinload(Account.check_configs))
            .where(Account.id == account_id)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def get_accounts_by_customer(
        self, customer_id: str, active_only: bool = True
    ) -> list[Account]:
        stmt = select(Account).where(Account.customer_id == customer_id)
        if active_only:
            stmt = stmt.where(Account.is_active == True)  # noqa: E712
        stmt = stmt.order_by(Account.display_name)
        return list(self.session.execute(stmt).scalars().all())

    def update_account(self, record_id: str, **kwargs) -> Account | None:
        account = self.get_account(record_id)
        if account is None:
            return None
        for key, value in kwargs.items():
            if hasattr(account, key):
                setattr(account, key, value)
        account.updated_at = datetime.now(timezone.utc)
        self.session.flush()
        return account

    # -- Account Check Config CRUD --

    def list_account_check_configs(self, account_id: str) -> list[AccountCheckConfig]:
        stmt = (
            select(AccountCheckConfig)
            .where(AccountCheckConfig.account_id == account_id)
            .order_by(AccountCheckConfig.check_name)
        )
        return list(self.session.execute(stmt).scalars().all())

    def upsert_account_check_config(
        self, account_id: str, check_name: str, config: dict
    ) -> AccountCheckConfig:
        stmt = select(AccountCheckConfig).where(
            AccountCheckConfig.account_id == account_id,
            AccountCheckConfig.check_name == check_name,
        )
        existing = self.session.execute(stmt).scalar_one_or_none()
        if existing:
            existing.config = config
            self.session.flush()
            return existing

        row = AccountCheckConfig(
            account_id=account_id,
            check_name=check_name,
            config=config,
        )
        self.session.add(row)
        self.session.flush()
        self.session.refresh(row)
        return row

    def delete_account_check_config(self, account_id: str, check_name: str) -> bool:
        stmt = select(AccountCheckConfig).where(
            AccountCheckConfig.account_id == account_id,
            AccountCheckConfig.check_name == check_name,
        )
        row = self.session.execute(stmt).scalar_one_or_none()
        if row is None:
            return False
        self.session.delete(row)
        self.session.flush()
        return True

    def delete_account(self, account_id: str) -> bool:
        account = self.get_account(account_id)
        if account is None:
            return False
        self.session.delete(account)
        self.session.flush()
        return True

    def get_mapped_profiles(self) -> list[str]:
        """Return all profile_names currently mapped to any customer."""
        stmt = select(Account.profile_name).distinct()
        return list(self.session.execute(stmt).scalars().all())

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()
