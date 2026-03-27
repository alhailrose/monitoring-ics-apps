"""Repository for check runs and results persistence."""

import calendar
import threading
import time
from datetime import datetime, timedelta, timezone
from statistics import fmean

from sqlalchemy import Date, cast, select, func
from sqlalchemy.orm import Session, selectinload

from backend.domain.metric_samples import WORKLOAD_METRIC_SAMPLE_CHECKS

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
            keys_to_delete = [
                k for k in _summary_cache if k.startswith(f"{customer_id}:")
            ]
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
        check_name: str | None = None,
    ) -> list[FindingEvent]:
        """Upsert findings: update last_seen_at for existing active findings,
        insert new ones, and resolve findings no longer present."""
        now = datetime.now(timezone.utc)

        # Determine which check_names should be synchronized.
        # check_name allows resolving stale active findings even when events is empty.
        check_names = {e["check_name"] for e in events}
        if check_name:
            check_names.add(check_name)

        if not check_names:
            return []

        # Load currently active findings for each check_name in this batch
        active: list[FindingEvent] = []
        for chk in check_names:
            stmt = select(FindingEvent).where(
                FindingEvent.account_id == account_id,
                FindingEvent.check_name == chk,
                FindingEvent.status == "active",
            )
            active.extend(self.session.execute(stmt).scalars().all())

        active_by_key: dict[tuple[str, str], FindingEvent] = {
            (f.check_name, f.finding_key): f for f in active
        }
        incoming_keys = {(e["check_name"], e["finding_key"]) for e in events}

        new_rows: list[FindingEvent] = []
        for event in events:
            key = (event["check_name"], event["finding_key"])
            if key in active_by_key:
                existing = active_by_key[key]
                existing.last_seen_at = now
                existing.check_run_id = check_run_id
                existing.title = event["title"]
                existing.description = event.get("description")
                existing.raw_payload = event.get("raw_payload")
            else:
                new_rows.append(
                    FindingEvent(
                        check_run_id=check_run_id,
                        account_id=account_id,
                        check_name=event["check_name"],
                        finding_key=event["finding_key"],
                        severity=event["severity"],
                        title=event["title"],
                        description=event.get("description"),
                        raw_payload=event.get("raw_payload"),
                        status="active",
                        last_seen_at=now,
                    )
                )

        # Resolve active findings no longer in the current check result
        for key, finding in active_by_key.items():
            if key not in incoming_keys:
                finding.status = "resolved"
                finding.resolved_at = now

        if new_rows:
            self.session.add_all(new_rows)
        self.session.flush()
        return new_rows

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

        from sqlalchemy.orm import selectinload

        stmt = (
            base.options(selectinload(CheckRun.customer))
            .order_by(CheckRun.created_at.desc())
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
            items.append(
                {
                    "check_run_id": run.id,
                    "customer": {
                        "id": run.customer.id,
                        "name": run.customer.name,
                        "display_name": run.customer.display_name,
                    },
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
                }
            )

        return items, total

    def list_findings(
        self,
        customer_id: str | None = None,
        check_name: str | None = None,
        severity: str | None = None,
        account_id: str | None = None,
        status: str | None = "active",
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[FindingEvent], int]:
        base = select(FindingEvent).join(
            CheckRun, FindingEvent.check_run_id == CheckRun.id
        )
        if customer_id:
            base = base.where(CheckRun.customer_id == customer_id)
        if check_name:
            base = base.where(FindingEvent.check_name == check_name)
        if severity:
            base = base.where(FindingEvent.severity == severity)
        if account_id:
            base = base.where(FindingEvent.account_id == account_id)
        if status:
            base = base.where(FindingEvent.status == status)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = self.session.execute(count_stmt).scalar_one()

        stmt = (
            base.options(
                selectinload(FindingEvent.account).selectinload(Account.customer)
            )
            .order_by(
                FindingEvent.last_seen_at.desc().nulls_last(),
                FindingEvent.created_at.desc(),
            )
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
        base = select(MetricSample).join(
            CheckRun, MetricSample.check_run_id == CheckRun.id
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
            base.options(
                selectinload(MetricSample.account).selectinload(Account.customer)
            )
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

        stmt = stmt.group_by(
            date_col, MetricSample.metric_name, MetricSample.account_id
        ).order_by(date_col)
        rows = self.session.execute(stmt).all()

        # Resolve account display names in one query
        account_ids = list({row.account_id for row in rows})
        accounts: dict[str, str] = {}
        if account_ids:
            accs = (
                self.session.execute(select(Account).where(Account.id.in_(account_ids)))
                .scalars()
                .all()
            )
            accounts = {a.id: a.display_name for a in accs}

        return [
            {
                "date": str(row.date),
                "metric_name": row.metric_name,
                "account_id": row.account_id,
                "account_display_name": accounts.get(row.account_id, row.account_id),
                "avg_value": float(row.avg_value)
                if row.avg_value is not None
                else None,
                "max_value": float(row.max_value)
                if row.max_value is not None
                else None,
                "sample_count": int(row.sample_count),
            }
            for row in rows
        ]

    def get_workload_monthly_report(
        self,
        customer_id: str,
        year: int | None = None,
        month: int | None = None,
        target_runs_per_day: int = 2,
        stuck_days_threshold: int = 7,
    ) -> dict:
        wib = timezone(timedelta(hours=7))
        now_wib = datetime.now(wib)
        selected_year = year or now_wib.year
        selected_month = month or now_wib.month

        start_wib = datetime(selected_year, selected_month, 1, tzinfo=wib)
        if selected_month == 12:
            end_wib = datetime(selected_year + 1, 1, 1, tzinfo=wib)
        else:
            end_wib = datetime(selected_year, selected_month + 1, 1, tzinfo=wib)

        start_utc = start_wib.astimezone(timezone.utc)
        end_utc = end_wib.astimezone(timezone.utc)

        run_rows = self.session.execute(
            select(CheckRun.id, CheckRun.created_at)
            .join(MetricSample, MetricSample.check_run_id == CheckRun.id)
            .where(
                CheckRun.customer_id == customer_id,
                CheckRun.created_at >= start_utc,
                CheckRun.created_at < end_utc,
                MetricSample.check_name.in_(tuple(WORKLOAD_METRIC_SAMPLE_CHECKS)),
            )
            .distinct()
        ).all()

        runs_by_day: dict[str, int] = {}
        for row in run_rows:
            day_key = row.created_at.astimezone(wib).date().isoformat()
            runs_by_day[day_key] = runs_by_day.get(day_key, 0) + 1

        days_in_month = calendar.monthrange(selected_year, selected_month)[1]
        if selected_year == now_wib.year and selected_month == now_wib.month:
            days_considered = now_wib.day
        else:
            days_considered = days_in_month

        daily_runs = []
        for day in range(1, days_considered + 1):
            date_key = (
                datetime(selected_year, selected_month, day, tzinfo=wib)
                .date()
                .isoformat()
            )
            daily_runs.append(
                {"date": date_key, "runs": int(runs_by_day.get(date_key, 0))}
            )

        expected_runs = days_considered * max(target_runs_per_day, 1)
        total_runs = int(sum(item["runs"] for item in daily_runs))
        days_met_target = int(
            sum(1 for item in daily_runs if item["runs"] >= max(target_runs_per_day, 1))
        )
        days_missing = [
            item for item in daily_runs if item["runs"] < max(target_runs_per_day, 1)
        ]

        metric_rows = self.session.execute(
            select(
                MetricSample.metric_name,
                MetricSample.value_num,
                MetricSample.created_at,
            )
            .join(CheckRun, MetricSample.check_run_id == CheckRun.id)
            .where(
                CheckRun.customer_id == customer_id,
                MetricSample.created_at >= start_utc,
                MetricSample.created_at < end_utc,
                MetricSample.check_name.in_(tuple(WORKLOAD_METRIC_SAMPLE_CHECKS)),
                MetricSample.value_num.is_not(None),
            )
        ).all()

        per_metric_values: dict[str, list[float]] = {}
        per_metric_daily: dict[str, dict[str, list[float]]] = {}
        for metric_name, value_num, created_at in metric_rows:
            if value_num is None:
                continue
            metric = str(metric_name)
            val = float(value_num)
            date_key = created_at.astimezone(wib).date().isoformat()
            per_metric_values.setdefault(metric, []).append(val)
            per_metric_daily.setdefault(metric, {}).setdefault(date_key, []).append(val)

        fluctuation_items = []
        for metric, values in per_metric_values.items():
            daily_map = per_metric_daily.get(metric, {})
            daily_avg_values = [fmean(vs) for vs in daily_map.values() if vs]
            daily_avg_range = (
                max(daily_avg_values) - min(daily_avg_values)
                if daily_avg_values
                else 0.0
            )
            fluctuation_items.append(
                {
                    "metric_name": metric,
                    "sample_count": len(values),
                    "days_with_samples": len(daily_map),
                    "avg_value": fmean(values),
                    "min_value": min(values),
                    "max_value": max(values),
                    "daily_avg_range": float(daily_avg_range),
                }
            )

        fluctuation_items.sort(
            key=lambda item: (
                item["daily_avg_range"],
                item["sample_count"],
            ),
            reverse=True,
        )

        metric_daily_series = []
        for metric, daily_map in per_metric_daily.items():
            points = []
            for date_key in sorted(daily_map.keys()):
                vals = daily_map.get(date_key) or []
                if not vals:
                    continue
                points.append(
                    {
                        "date": date_key,
                        "avg_value": float(fmean(vals)),
                        "max_value": float(max(vals)),
                    }
                )
            if not points:
                continue

            daily_avg_values = [p["avg_value"] for p in points]
            daily_avg_range = (
                max(daily_avg_values) - min(daily_avg_values)
                if daily_avg_values
                else 0.0
            )
            metric_daily_series.append(
                {
                    "metric_name": metric,
                    "daily_avg_range": float(daily_avg_range),
                    "points": points,
                }
            )

        metric_daily_series.sort(
            key=lambda item: item["daily_avg_range"],
            reverse=True,
        )

        resource_rows = self.session.execute(
            select(
                Account.display_name,
                MetricSample.resource_id,
                MetricSample.resource_name,
                MetricSample.metric_name,
                MetricSample.value_num,
                MetricSample.created_at,
            )
            .join(CheckRun, MetricSample.check_run_id == CheckRun.id)
            .join(Account, Account.id == MetricSample.account_id)
            .where(
                CheckRun.customer_id == customer_id,
                MetricSample.created_at >= start_utc,
                MetricSample.created_at < end_utc,
                MetricSample.check_name.in_(tuple(WORKLOAD_METRIC_SAMPLE_CHECKS)),
                MetricSample.value_num.is_not(None),
            )
        ).all()

        resource_metric_values: dict[tuple[str, str, str], list[float]] = {}
        resource_metric_daily: dict[tuple[str, str, str], dict[str, list[float]]] = {}
        resource_metric_names: dict[tuple[str, str, str], str] = {}
        for (
            account_name,
            resource_id,
            resource_name,
            metric_name,
            value_num,
            created_at,
        ) in resource_rows:
            if value_num is None:
                continue
            acct = str(account_name or "Unknown Account")
            rid = str(resource_id or resource_name or "unknown-resource")
            mname = str(metric_name)
            key = (acct, rid, mname)
            val = float(value_num)
            date_key = created_at.astimezone(wib).date().isoformat()
            resource_metric_values.setdefault(key, []).append(val)
            resource_metric_daily.setdefault(key, {}).setdefault(date_key, []).append(
                val
            )
            resource_metric_names[key] = str(resource_name or resource_id or "")

        resource_fluctuations = []
        for key, values in resource_metric_values.items():
            acct, rid, mname = key
            daily_map = resource_metric_daily.get(key, {})
            daily_avg_values = [fmean(vs) for vs in daily_map.values() if vs]
            daily_avg_range = (
                max(daily_avg_values) - min(daily_avg_values)
                if daily_avg_values
                else 0.0
            )
            resource_fluctuations.append(
                {
                    "account_display_name": acct,
                    "resource_id": rid,
                    "resource_name": resource_metric_names.get(key) or rid,
                    "metric_name": mname,
                    "sample_count": len(values),
                    "days_with_samples": len(daily_map),
                    "avg_value": fmean(values),
                    "min_value": min(values),
                    "max_value": max(values),
                    "daily_avg_range": float(daily_avg_range),
                }
            )

        resource_fluctuations.sort(
            key=lambda item: (
                item["daily_avg_range"],
                item["sample_count"],
            ),
            reverse=True,
        )

        resource_daily_series = []
        for key, daily_map in resource_metric_daily.items():
            acct, rid, mname = key
            points = []
            for date_key in sorted(daily_map.keys()):
                vals = daily_map.get(date_key) or []
                if not vals:
                    continue
                points.append(
                    {
                        "date": date_key,
                        "avg_value": float(fmean(vals)),
                        "max_value": float(max(vals)),
                    }
                )
            if not points:
                continue

            daily_avg_values = [p["avg_value"] for p in points]
            daily_avg_range = (
                max(daily_avg_values) - min(daily_avg_values)
                if daily_avg_values
                else 0.0
            )

            resource_daily_series.append(
                {
                    "account_display_name": acct,
                    "resource_id": rid,
                    "resource_name": resource_metric_names.get(key) or rid,
                    "metric_name": mname,
                    "daily_avg_range": float(daily_avg_range),
                    "points": points,
                }
            )

        resource_daily_series.sort(
            key=lambda item: item["daily_avg_range"],
            reverse=True,
        )

        # Active/stuck findings overview (customer-facing risk highlights)
        active_issue_rows = self.session.execute(
            select(
                FindingEvent.check_name,
                FindingEvent.severity,
                FindingEvent.title,
                FindingEvent.created_at,
                FindingEvent.last_seen_at,
                Account.display_name,
            )
            .join(Account, Account.id == FindingEvent.account_id)
            .where(
                Account.customer_id == customer_id,
                FindingEvent.status == "active",
                FindingEvent.check_name.in_(("guardduty", "cloudwatch")),
            )
        ).all()

        now_utc = datetime.now(timezone.utc)
        stuck_items = []
        guardduty_active = 0
        cloudwatch_active = 0
        guardduty_stuck = 0
        cloudwatch_stuck = 0

        for (
            check_name,
            severity,
            title,
            created_at,
            last_seen_at,
            account_display,
        ) in active_issue_rows:
            age_days = max(0, int((now_utc - created_at).total_seconds() // 86400))
            if check_name == "guardduty":
                guardduty_active += 1
                if age_days >= stuck_days_threshold:
                    guardduty_stuck += 1
            elif check_name == "cloudwatch":
                cloudwatch_active += 1
                if age_days >= stuck_days_threshold:
                    cloudwatch_stuck += 1

            if age_days >= stuck_days_threshold:
                stuck_items.append(
                    {
                        "check_name": str(check_name),
                        "account_display_name": str(
                            account_display or "Unknown Account"
                        ),
                        "severity": str(severity or "ALARM"),
                        "title": str(title or "issue"),
                        "age_days": age_days,
                        "last_seen_at": (
                            last_seen_at.isoformat()
                            if last_seen_at is not None
                            else created_at.isoformat()
                        ),
                    }
                )

        stuck_items.sort(key=lambda item: item["age_days"], reverse=True)

        # Cost anomaly highlights by account (monthly peak)
        cost_rows = self.session.execute(
            select(
                Account.display_name,
                MetricSample.metric_name,
                func.max(MetricSample.value_num).label("peak_value"),
            )
            .join(CheckRun, MetricSample.check_run_id == CheckRun.id)
            .join(Account, Account.id == MetricSample.account_id)
            .where(
                CheckRun.customer_id == customer_id,
                MetricSample.created_at >= start_utc,
                MetricSample.created_at < end_utc,
                MetricSample.check_name == "cost",
                MetricSample.metric_name.in_(("anomalies_today", "anomalies_total")),
                MetricSample.value_num.is_not(None),
            )
            .group_by(Account.display_name, MetricSample.metric_name)
        ).all()

        cost_by_account: dict[str, dict[str, float]] = {}
        for account_display, metric_name, peak_value in cost_rows:
            account_name = str(account_display or "Unknown Account")
            metric = str(metric_name)
            cost_by_account.setdefault(account_name, {})[metric] = float(
                peak_value or 0.0
            )

        cost_accounts = []
        for account_name, metrics in cost_by_account.items():
            peak_today = float(metrics.get("anomalies_today", 0.0))
            peak_total = float(metrics.get("anomalies_total", 0.0))
            if peak_today <= 0 and peak_total <= 0:
                continue
            cost_accounts.append(
                {
                    "account_display_name": account_name,
                    "anomalies_today_peak": peak_today,
                    "anomalies_total_peak": peak_total,
                }
            )

        cost_accounts.sort(
            key=lambda item: (
                item["anomalies_today_peak"],
                item["anomalies_total_peak"],
            ),
            reverse=True,
        )

        completion_rate = (
            (total_runs / expected_runs * 100.0) if expected_runs > 0 else 0.0
        )

        return {
            "customer_id": customer_id,
            "month": f"{selected_year:04d}-{selected_month:02d}",
            "target_runs_per_day": max(target_runs_per_day, 1),
            "days_in_month": days_in_month,
            "days_considered": days_considered,
            "coverage": {
                "total_runs": total_runs,
                "expected_runs": expected_runs,
                "completion_rate": round(completion_rate, 2),
                "days_met_target": days_met_target,
                "days_missing_target": len(days_missing),
            },
            "daily_runs": daily_runs,
            "top_missing_days": days_missing[:10],
            "metric_fluctuations": fluctuation_items,
            "metric_daily_series": metric_daily_series[:20],
            "resource_fluctuations": resource_fluctuations[:200],
            "resource_daily_series": resource_daily_series[:30],
            "stuck_summary": {
                "threshold_days": stuck_days_threshold,
                "guardduty_active": guardduty_active,
                "cloudwatch_active": cloudwatch_active,
                "guardduty_stuck": guardduty_stuck,
                "cloudwatch_stuck": cloudwatch_stuck,
                "items": stuck_items[:50],
            },
            "cost_summary": {
                "impacted_accounts": len(cost_accounts),
                "accounts": cost_accounts[:50],
            },
        }

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
                .where(
                    *run_filter,
                    MetricSample.check_name.in_(tuple(WORKLOAD_METRIC_SAMPLE_CHECKS)),
                )
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

    def get_customers_overview(self) -> list[dict]:
        """Return a per-customer summary for the global overview dashboard."""
        since_24h = datetime.now(timezone.utc) - timedelta(hours=24)

        # All customers (via Account → Customer relationship)
        customers = (
            self.session.execute(
                select(Customer).options(selectinload(Customer.accounts))
            )
            .scalars()
            .all()
        )

        if not customers:
            return []

        customer_ids = [c.id for c in customers]

        # Latest run per customer
        latest_run_rows = self.session.execute(
            select(CheckRun.customer_id, func.max(CheckRun.created_at))
            .where(CheckRun.customer_id.in_(customer_ids))
            .group_by(CheckRun.customer_id)
        ).all()
        latest_run: dict[str, datetime] = {r[0]: r[1] for r in latest_run_rows}

        # Last 24h result counts per customer
        result_rows = self.session.execute(
            select(CheckRun.customer_id, CheckResult.status, func.count(CheckResult.id))
            .join(CheckResult, CheckResult.check_run_id == CheckRun.id)
            .where(
                CheckRun.customer_id.in_(customer_ids), CheckRun.created_at >= since_24h
            )
            .group_by(CheckRun.customer_id, CheckResult.status)
        ).all()
        result_counts: dict[str, dict[str, int]] = {}
        for cid, status, cnt in result_rows:
            result_counts.setdefault(cid, {})[status] = int(cnt)

        # Active findings per customer (via account)
        account_to_customer = {
            acc.id: acc.customer_id for c in customers for acc in c.accounts
        }
        finding_rows = self.session.execute(
            select(
                FindingEvent.account_id,
                FindingEvent.severity,
                func.count(FindingEvent.id),
            )
            .where(
                FindingEvent.account_id.in_(list(account_to_customer.keys())),
                FindingEvent.status == "active",
            )
            .group_by(FindingEvent.account_id, FindingEvent.severity)
        ).all()
        findings_by_customer: dict[str, dict[str, int]] = {}
        for acc_id, severity, cnt in finding_rows:
            cid = account_to_customer.get(acc_id)
            if cid:
                findings_by_customer.setdefault(cid, {})[severity] = int(cnt)

        results = []
        for customer in customers:
            cid = customer.id
            rc = result_counts.get(cid, {})
            fc = findings_by_customer.get(cid, {})
            total_findings = sum(fc.values())
            has_critical = fc.get("CRITICAL", 0) > 0 or fc.get("ALARM", 0) > 0
            has_warn = (
                fc.get("HIGH", 0) > 0
                or fc.get("MEDIUM", 0) > 0
                or rc.get("WARN", 0) > 0
                or rc.get("ERROR", 0) > 0
            )

            if has_critical or rc.get("ERROR", 0) > 0:
                health = "error"
            elif has_warn:
                health = "warn"
            elif total_findings > 0:
                health = "warn"
            else:
                health = "ok"

            results.append(
                {
                    "customer_id": cid,
                    "customer_name": customer.display_name,
                    "health": health,
                    "active_findings": total_findings,
                    "findings_by_severity": fc,
                    "results_24h": {
                        "ok": rc.get("OK", 0),
                        "warn": rc.get("WARN", 0),
                        "error": rc.get("ERROR", 0),
                    },
                    "last_run_at": latest_run.get(cid),
                }
            )

        results.sort(
            key=lambda x: (
                {"error": 0, "warn": 1, "ok": 2}[x["health"]],
                x["customer_name"],
            )
        )
        return results

    # -- Internal --

    def _get_run(self, check_run_id: str) -> CheckRun | None:
        stmt = select(CheckRun).where(CheckRun.id == check_run_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()
