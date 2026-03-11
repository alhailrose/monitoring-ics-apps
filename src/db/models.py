"""SQLAlchemy models for monitoring platform."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    checks: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    slack_webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    slack_channel: Mapped[str | None] = mapped_column(String(128), nullable=True)
    slack_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sso_session: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False)

    accounts: Mapped[list[Account]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    check_runs: Mapped[list[CheckRun]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="noload",
    )


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("customer_id", "profile_name", name="uq_customer_profile"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    profile_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    account_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config_extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    region: Mapped[str | None] = mapped_column(Text, nullable=True)
    alarm_names: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False)

    customer: Mapped[Customer] = relationship(back_populates="accounts")
    check_results: Mapped[list[CheckResult]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
        lazy="noload",
    )


class CheckRun(Base):
    __tablename__ = "check_runs"
    __table_args__ = (
        CheckConstraint(
            "check_mode in ('single','all','arbel')",
            name="ck_check_runs_mode_valid",
        ),
        Index("idx_check_runs_customer_created", "customer_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    check_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    check_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    requested_by: Mapped[str] = mapped_column(String(64), nullable=False, default="web")
    slack_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    execution_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)

    customer: Mapped[Customer] = relationship(back_populates="check_runs")
    results: Mapped[list[CheckResult]] = relationship(
        back_populates="check_run",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CheckResult(Base):
    __tablename__ = "check_results"
    __table_args__ = (
        CheckConstraint(
            "status in ('OK','WARN','ERROR','ALARM','NO_DATA')",
            name="ck_check_results_status_valid",
        ),
        Index("idx_check_results_account_check", "account_id", "check_name", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    check_run_id: Mapped[str] = mapped_column(ForeignKey("check_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    check_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    output: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)

    check_run: Mapped[CheckRun] = relationship(back_populates="results")
    account: Mapped[Account] = relationship(back_populates="check_results")
