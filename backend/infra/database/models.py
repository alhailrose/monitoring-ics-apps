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


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role in ('super_user','user')", name="ck_users_role_valid"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    username: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str | None] = mapped_column(String(256), nullable=True)
    email: Mapped[str | None] = mapped_column(
        String(256), unique=True, nullable=True, index=True
    )
    google_sub: Mapped[str | None] = mapped_column(
        String(256), unique=True, nullable=True, index=True
    )
    auth_provider: Mapped[str] = mapped_column(
        String(32), nullable=False, default="password"
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False
    )


class Invite(Base):
    __tablename__ = "invites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    token: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="user")
    invited_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    accepted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        CheckConstraint(
            "status in ('open','in_progress','resolved','closed')",
            name="ck_tickets_status_valid",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    ticket_no: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )
    task: Mapped[str] = mapped_column(String(512), nullable=False)
    pic: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    description_solution: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False
    )


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(
        String(128), unique=True, nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    checks: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    slack_webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    slack_channel: Mapped[str | None] = mapped_column(String(128), nullable=True)
    slack_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sso_session: Mapped[str | None] = mapped_column(String(128), nullable=True)
    report_mode: Mapped[str] = mapped_column(
        String(32), nullable=False, default="summary"
    )
    label: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False
    )

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
    customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    profile_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    account_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config_extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    region: Mapped[str | None] = mapped_column(Text, nullable=True)
    alarm_names: Mapped[list | None] = mapped_column(JSON, nullable=True)
    auth_method: Mapped[str] = mapped_column(
        String(16), nullable=False, default="profile"
    )
    aws_access_key_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    aws_secret_access_key_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    role_arn: Mapped[str | None] = mapped_column(String(512), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False
    )

    customer: Mapped[Customer] = relationship(back_populates="accounts")
    check_results: Mapped[list[CheckResult]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    finding_events: Mapped[list[FindingEvent]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    check_configs: Mapped[list[AccountCheckConfig]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    metric_samples: Mapped[list[MetricSample]] = relationship(
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
    customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    check_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    check_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    requested_by: Mapped[str] = mapped_column(String(64), nullable=False, default="web")
    slack_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    execution_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )

    customer: Mapped[Customer] = relationship(back_populates="check_runs")
    results: Mapped[list[CheckResult]] = relationship(
        back_populates="check_run",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    finding_events: Mapped[list[FindingEvent]] = relationship(
        back_populates="check_run",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    metric_samples: Mapped[list[MetricSample]] = relationship(
        back_populates="check_run",
        cascade="all, delete-orphan",
        lazy="noload",
    )


class CheckResult(Base):
    __tablename__ = "check_results"
    __table_args__ = (
        CheckConstraint(
            "status in ('OK','WARN','ERROR','ALARM','NO_DATA')",
            name="ck_check_results_status_valid",
        ),
        Index(
            "idx_check_results_account_check", "account_id", "check_name", "created_at"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    check_run_id: Mapped[str] = mapped_column(
        ForeignKey("check_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    check_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    output: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )

    check_run: Mapped[CheckRun] = relationship(back_populates="results")
    account: Mapped[Account] = relationship(back_populates="check_results")


class FindingEvent(Base):
    __tablename__ = "finding_events"
    __table_args__ = (
        CheckConstraint(
            "severity in ('INFO','LOW','MEDIUM','HIGH','CRITICAL','ALARM')",
            name="ck_finding_events_severity_valid",
        ),
        Index(
            "idx_finding_events_account_check", "account_id", "check_name", "created_at"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    check_run_id: Mapped[str] = mapped_column(
        ForeignKey("check_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    check_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    finding_key: Mapped[str] = mapped_column(String(256), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )

    check_run: Mapped[CheckRun] = relationship(back_populates="finding_events")
    account: Mapped[Account] = relationship(back_populates="finding_events")


class AccountCheckConfig(Base):
    __tablename__ = "account_check_configs"
    __table_args__ = (
        UniqueConstraint("account_id", "check_name", name="uq_account_check_config"),
        Index("idx_account_check_config_account", "account_id"),
        Index("idx_account_check_config_check", "check_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    check_name: Mapped[str] = mapped_column(String(128), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False
    )

    account: Mapped[Account] = relationship(back_populates="check_configs")


class MetricSample(Base):
    __tablename__ = "metric_samples"
    __table_args__ = (
        Index(
            "idx_metric_samples_account_metric",
            "account_id",
            "metric_name",
            "created_at",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    check_run_id: Mapped[str] = mapped_column(
        ForeignKey("check_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_id: Mapped[str] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    check_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    metric_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    metric_status: Mapped[str] = mapped_column(String(32), nullable=False)
    value_num: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_role: Mapped[str | None] = mapped_column(String(128), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    resource_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    service_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    section_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utc_now, nullable=False
    )

    check_run: Mapped[CheckRun] = relationship(back_populates="metric_samples")
    account: Mapped[Account] = relationship(back_populates="metric_samples")
