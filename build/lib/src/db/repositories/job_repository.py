"""Repository for job and normalized result persistence."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.db.models import Job, JobResult


class JobRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_job(self, customer_id: str, check_name: str, requested_by: str) -> Job:
        job = Job(
            customer_id=customer_id,
            check_name=check_name,
            requested_by=requested_by,
            status="queued",
        )
        self.session.add(job)
        self.session.flush()
        self.session.refresh(job)
        return job

    def add_result(self, job_id: str, profile: str, status: str, normalized: dict) -> JobResult:
        result = JobResult(
            job_id=job_id,
            profile=profile,
            status=status,
            normalized=normalized,
        )
        self.session.add(result)
        self.session.flush()
        self.session.refresh(result)
        return result

    def get_job(self, job_id: str) -> Job | None:
        stmt = (
            select(Job)
            .options(selectinload(Job.results))
            .where(Job.id == job_id)
            .execution_options(populate_existing=True)
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def list_history(self, customer_id: str) -> list[dict]:
        stmt = (
            select(Job)
            .options(selectinload(Job.results))
            .where(Job.customer_id == customer_id)
            .order_by(Job.created_at.desc())
        )
        jobs = self.session.execute(stmt).scalars().all()

        items = []
        for job in jobs:
            items.append(
                {
                    "job_id": job.id,
                    "customer_id": job.customer_id,
                    "check_name": job.check_name,
                    "status": job.status,
                    "created_at": job.created_at.isoformat(),
                    "results": [
                        {
                            "profile": r.profile,
                            "status": r.status,
                            "normalized": r.normalized,
                        }
                        for r in job.results
                    ],
                }
            )
        return items

    def mark_running(self, job_id: str):
        job = self.get_job(job_id)
        if job is None:
            return
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        job.last_error = None
        self.session.flush()

    def mark_completed(self, job_id: str):
        job = self.get_job(job_id)
        if job is None:
            return
        job.status = "completed"
        job.finished_at = datetime.now(timezone.utc)
        self.session.flush()

    def mark_failed(self, job_id: str, error: str):
        job = self.get_job(job_id)
        if job is None:
            return
        job.status = "failed"
        job.last_error = error[:1024]
        job.finished_at = datetime.now(timezone.utc)
        self.session.flush()

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()
