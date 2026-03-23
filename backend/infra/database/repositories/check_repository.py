"""Repository for check runs and results persistence."""

import threading
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import Date, cast, select, func
from sqlalchemy.orm import Session, selectinload

from backend.infra.database.models import (
    Account,
    CheckResult,
    CheckRun,
    Customer,
    FindingEvent,
    MetricSample,
)

# ---------------------------------------------------------------------------
# Dashboard summary in-memory cache (TTL = 5 minutes)
# Avoids 6 COUNT queries on every dashboard refresh.
# ---------------------------------------------------------------------------
_SUMMARY_TTL = 300  # seconds
_summary_cache: dict[str, tuple[dict, float]] = {}
_summary_lock = threading.Lock()


def _get_cached_summary(key: str) -> dict | None:
    with _summary_lock:
        entry = _summary_cache.get(key)
    if entry is None:
        return None
    data, expires_at = entry
    return data if time.monotonic() < expires_at else None


def _set_cached_summary(key: str, data: dict) -> None:
    with _summary_lock:
        _summary_cache[key] = (data, time.monotonic() + _SUMMARY_TTL)


def invalidate_summary_cache(customer_id: str | None = None) -> None:
    """Call after a new check run completes to invalidate stale summaries."""
    with _summary_lock:
        if customer_id:
            keys_to_delete = [k for k in _summary_cache if k.startswith(f"{customer_id}:")]
            for k in keys_to_delete:
                del _summary_cache[k]
        else:
            _summary_cache.clear()


class CheckRepository:
    def __init__(self, session: Session):
        self.session = session

    # -- CheckRun --

    def create_check_run(
        self,
        customer_id: str,
        check_mode: str,
        check_name: str | None = None,
        requested_by: str = "web",
    ) -> CheckRun:
        run = CheckRun(
            customer_id=customer_id,
            check_mode=check_mode,
            check_name=check_name,
            requested_by=requested_by,
        )
        self.session.add(run)
        self.session.flush()
        self.session.refresh(run)
        return run

    def finish_check_run(
        self,
        check_run_id: str,
        execution_time_seconds: float,
        slack_sent: bool = False,
    ):
        run = self._get_run(check_run_id)
        if run is None:
            return
        run.execution_time_seconds = execution_time_seconds
        run.slack_sent = slack_sent
        self.session.flush()

    # -- CheckResult --

    def add_result(
        self,
        check_run_id: str,
        account_id: str,
        check_name: str,
        status: str,
        summary: str | None = None,
        output: str | None = None,
        details: dict | None = None,
    ) -> CheckResult:
        result = CheckResult(
            check_run_id=check_run_id,
            account_id=account_id,
            check_name=check_name,
            status=status,
            summary=summary,
            output=output,
            details=details,
        )
        self.session.add(result)
        self.session.flush()
        return result

    def add_finding_events(
        self,
        check_run_id: str,
        account_id: str,
        events: list[dict],
    ) -> list[FindingEvent]:
        if not events:
            return []

        rows: list[FindingEvent] = []
        for event in events:
            row = FindingEvent(
                check_run_id=check_run_id,
                account_id=account_id,
                check_name=event["check_name"],
                finding_key=event["finding_key"],
                severity=event["severity"],
                title=event["title"],
                description=event.get("description"),
                raw_payload=event.get("raw_payload"),
            )
            rows.append(row)

        self.session.add_all(rows)
        self.session.flush()
        return rows

    def add_metric_samples(
        self,
        check_run_id: str,
        account_id: str,
        samples: list[dict],
    ) -> list[MetricSample]:
        if not samples:
            return []

        rows: list[MetricSample] = []
        for sample in samples:
            row = MetricSample(
                check_run_id=check_run_id,
                account_id=account_id,
                check_name=sample["check_name"],
                metric_name=sample["metric_name"],
                metric_status=sample["metric_status"],
                value_num=sample.get("value_num"),
                unit=sample.get("unit"),
                resource_role=sample.get("resource_role"),
                resource_id=sample.get("resource_id"),
                resource_name=sample.get("resource_name"),
                service_type=sample.get("service_type"),
                section_name=sample.get("section_name"),
                raw_payload=sample.get("raw_payload"),
            )
            rows.append(row)

        self.session.add_all(rows)
        self.session.flush()
        return rows

    # -- History queries --

    def get_check_run(self, check_run_id: str) -> CheckRun | None:
        stmt = (
            select(CheckRun)
            .options(
                selectinload(CheckRun.results).selectinload(CheckResult.account),
                selectinload(CheckRun.customer),
            )
            .where(CheckRun.id == check_run_id)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_history(
        self,
        customer_id: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        check_mode: str | None = None,
        check_name: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[CheckRun], int]:
        """Return paginated check runs with total count."""
        base = select(CheckRun).where(CheckRun.customer_id == customer_id)

        if start_date:
            base = base.where(CheckRun.created_at >= start_date)
        if end_date:
            base = base.where(CheckRun.created_at <= end_date)
        if check_mode:
            base = base.where(CheckRun.check_mode == check_mode)
        if check_name:
            base = base.where(CheckRun.check_name == check_name)

        # Count
        count_stmt = select(func.count()).select_from(base.subquery())
        total = self.session.execute(count_stmt).scalar_one()

        # Fetch
        stmt = (
            base.options(selectinload(CheckRun.results))
            .order_by(CheckRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        runs = list(self.session.execute(stmt).scalars().all())
        return runs, total

    def list_history_summary(
        self,
        customer_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        check_mode: str | None = None,
        check_name: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """Return paginated check runs with status counts via SQL (no eager load)."""
        base = select(CheckRun)
        if customer_id:
            base = base.where(CheckRun.customer_id == customer_id)

        if start_date:
            base = base.where(CheckRun.created_at >= start_date)
        if end_date:
            base = base.where(CheckRun.created_at <= end_date)
        if check_mode:
            base = base.where(CheckRun.check_mode == check_mode)
        if check_name:
            base = base.where(CheckRun.check_name == check_name)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = self.session.execute(count_stmt).scalar_one()

        stmt = (
            base.order_by(CheckRun.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        runs = list(self.session.execute(stmt).scalars().all())

        if not runs:
            return [], total

        # Batch status counts in one query
        run_ids = [r.id for r in runs]
        count_rows = self.session.execute(
            select(
                CheckResult.check_run_id,
                CheckResult.status,
                func.count().label("cnt"),
            )
            .where(CheckResult.check_run_id.in_(run_ids))
            .group_by(CheckResult.check_run_id, CheckResult.status)
        ).all()

        counts_map: dict[str, dict[str, int]] = {}
        for run_id, status, cnt in count_rows:
            counts_map.setdefault(run_id, {})[status] = cnt

        items = []
        for run in runs:
            sc = counts_map.get(run.id, {})
            items.append({
                "check_run_id": run.id,
                "check_mode": run.check_mode,
                "check_name": run.check_name,
                "created_at": run.created_at.isoformat(),
                "execution_time_seconds": run.execution_time_seconds,
                "slack_sent": run.slack_sent,
                "results_summary": {
                    "total": sum(sc.values()),
                    "ok": sc.get("OK", 0),
                    "warn": sc.get("WARN", 0) + sc.get("ALARM", 0),
                    "error": sc.get("ERROR", 0),
                },
            })

        return items, total

    def list_findings(
        self,
        customer_id: str | None = None,
        check_name: str | None = None,
        severity: str | None = None,
        account_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[FindingEvent], int]:
        base = (
            select(FindingEvent)
            .join(CheckRun, FindingEvent.check_run_id == CheckRun.id)
        )
        if customer_id:
            base = base.where(CheckRun.customer_id == customer_id)

        if check_name:
            base = base.where(FindingEvent.check_name == check_name)
        if severity:
            base = base.where(FindingEvent.severity == severity)
        if account_id:
            base = base.where(FindingEvent.account_id == account_id)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = self.session.execute(count_stmt).scalar_one()

        stmt = (
            base.options(selectinload(FindingEvent.account).selectinload(Account.customer))
            .order_by(FindingEvent.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        findings = list(self.session.execute(stmt).scalars().all())
        return findings, total

    def list_metric_samples(
        self,
        customer_id: str | None = None,
        check_name: str | None = None,
        metric_name: str | None = None,
        metric_status: str | None = None,
        account_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[MetricSample], int]:
        base = (
            select(MetricSample)
            .join(CheckRun, MetricSample.check_run_id == CheckRun.id)
        )
        if customer_id:
            base = base.where(CheckRun.customer_id == customer_id)

        if check_name:
            base = base.where(MetricSample.check_name == check_name)
        if metric_name:
            base = base.where(MetricSample.metric_name == metric_name)
        if metric_status:
            base = base.where(MetricSample.metric_status == metric_status)
        if account_id:
            base = base.where(MetricSample.account_id == account_id)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = self.session.execute(count_stmt).scalar_one()

        stmt = (
            base.options(selectinload(MetricSample.account).selectinload(Account.customer))
            .order_by(MetricSample.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        samples = list(self.session.execute(stmt).scalars().all())
        return samples, total

    def get_metric_timeseries(
        self,
        check_name: str,
        customer_id: str | None = None,
        account_id: str | None = None,
        days: int = 14,
    ) -> list[dict]:
        """Return daily-aggregated metric values for charting."""
        since = datetime.now(timezone.utc) - timedelta(days=days)
        date_col = cast(MetricSample.created_at, Date).label("date")

        stmt = (
            select(
                date_col,
                MetricSample.metric_name,
                MetricSample.account_id,
                func.avg(MetricSample.value_num).label("avg_value"),
                func.max(MetricSample.value_num).label("max_value"),
                func.count().label("sample_count"),
            )
            .join(CheckRun, MetricSample.check_run_id == CheckRun.id)
            .where(
                MetricSample.check_name == check_name,
                MetricSample.created_at >= since,
                MetricSample.value_num.isnot(None),
            )
        )
        if customer_id:
            stmt = stmt.where(CheckRun.customer_id == customer_id)
        if account_id:
            stmt = stmt.where(MetricSample.account_id == account_id)

        stmt = (
            stmt
            .group_by(date_col, MetricSample.metric_name, MetricSample.account_id)
            .order_by(date_col)
        )
        rows = self.session.execute(stmt).all()

        # Resolve account display names in one query
        account_ids = list({row.account_id for row in rows})
        accounts: dict[str, str] = {}
        if account_ids:
            accs = self.session.execute(
                select(Account).where(Account.id.in_(account_ids))
            ).scalars().all()
            accounts = {a.id: a.display_name for a in accs}

        return [
            {
                "date": str(row.date),
                "metric_name": row.metric_name,
                "account_id": row.account_id,
                "account_display_name": accounts.get(row.account_id, row.account_id),
                "avg_value": float(row.avg_value) if row.avg_value is not None else None,
                "max_value": float(row.max_value) if row.max_value is not None else None,
                "sample_count": int(row.sample_count),
            }
            for row in rows
        ]

    def get_dashboard_summary(
        self,
        customer_id: str,
        window_hours: int = 24,
    ) -> dict:
        cache_key = f"{customer_id}:{window_hours}"
        cached = _get_cached_summary(cache_key)
        if cached is not None:
            return cached

        since = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        run_filter = (CheckRun.customer_id == customer_id, CheckRun.created_at >= since)

        total_runs = self.session.execute(
            select(func.count(CheckRun.id)).where(*run_filter)
        ).scalar_one()

        mode_counts = {
            row[0]: int(row[1])
            for row in self.session.execute(
                select(CheckRun.check_mode, func.count(CheckRun.id))
                .where(*run_filter)
                .group_by(CheckRun.check_mode)
            ).all()
        }

        latest_created_at = self.session.execute(
            select(func.max(CheckRun.created_at)).where(*run_filter)
        ).scalar_one_or_none()

        result_counts = {
            row[0]: int(row[1])
            for row in self.session.execute(
                select(CheckResult.status, func.count(CheckResult.id))
                .join(CheckRun, CheckResult.check_run_id == CheckRun.id)
                .where(*run_filter)
                .group_by(CheckResult.status)
            ).all()
        }

        findings_by_severity = {
            row[0]: int(row[1])
            for row in self.session.execute(
                select(FindingEvent.severity, func.count(FindingEvent.id))
                .join(CheckRun, FindingEvent.check_run_id == CheckRun.id)
                .where(*run_filter)
                .group_by(FindingEvent.severity)
            ).all()
        }

        metric_status_counts = {
            row[0]: int(row[1])
            for row in self.session.execute(
                select(MetricSample.metric_status, func.count(MetricSample.id))
                .join(CheckRun, MetricSample.check_run_id == CheckRun.id)
                .where(*run_filter)
                .group_by(MetricSample.metric_status)
            ).all()
        }

        top_checks_rows = self.session.execute(
            select(CheckRun.check_name, func.count(CheckRun.id))
            .where(*run_filter, CheckRun.check_name.is_not(None))
            .group_by(CheckRun.check_name)
            .order_by(func.count(CheckRun.id).desc())
            .limit(5)
        ).all()

        total_results = int(sum(result_counts.values()))
        total_findings = int(sum(findings_by_severity.values()))
        total_metrics = int(sum(metric_status_counts.values()))

        result = {
            "customer_id": customer_id,
            "window_hours": window_hours,
            "generated_at": datetime.now(timezone.utc),
            "since": since,
            "runs": {
                "total": int(total_runs),
                "single": int(mode_counts.get("single", 0)),
                "all": int(mode_counts.get("all", 0)),
                "arbel": int(mode_counts.get("arbel", 0)),
                "latest_created_at": latest_created_at,
            },
            "results": {
                "total": total_results,
                "ok": int(result_counts.get("OK", 0)),
                "warn": int(result_counts.get("WARN", 0)),
                "error": int(result_counts.get("ERROR", 0)),
                "alarm": int(result_counts.get("ALARM", 0)),
                "no_data": int(result_counts.get("NO_DATA", 0)),
            },
            "findings": {
                "total": total_findings,
                "by_severity": findings_by_severity,
            },
            "metrics": {
                "total": total_metrics,
                "by_status": metric_status_counts,
            },
            "top_checks": [
                {"check_name": str(row[0]), "runs": int(row[1])}
                for row in top_checks_rows
            ],
        }
        _set_cached_summary(cache_key, result)
        return result

    # -- Internal --

    def _get_run(self, check_run_id: str) -> CheckRun | None:
        stmt = select(CheckRun).where(CheckRun.id == check_run_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()
