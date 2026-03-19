"""Repository for check runs and results persistence."""

from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload

from backend.infra.database.models import Account, CheckResult, CheckRun, FindingEvent


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

    # -- Internal --

    def _get_run(self, check_run_id: str) -> CheckRun | None:
        stmt = select(CheckRun).where(CheckRun.id == check_run_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()
