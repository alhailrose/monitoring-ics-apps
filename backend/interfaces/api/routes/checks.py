"""Check execution endpoints."""

from datetime import datetime, timezone
from typing import Annotated
import logging
import threading
import time
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator, model_validator

from backend.interfaces.api.dependencies import (
    create_db_session,
    get_check_executor,
    require_auth,
)

# ---------------------------------------------------------------------------
# Simple in-memory rate limiter for /checks/execute
# Max 3 concurrent or recent executions per user within a 60-second window.
# ---------------------------------------------------------------------------
_RATE_WINDOW_SECONDS = 60
_RATE_MAX_CALLS = 3
_rate_store: dict[str, list[float]] = {}  # user_id → list of call timestamps
_rate_lock = threading.Lock()


def _check_rate_limit(user_id: str) -> None:
    now = time.monotonic()
    with _rate_lock:
        timestamps = _rate_store.get(user_id, [])
        # Drop timestamps outside the window
        timestamps = [t for t in timestamps if now - t < _RATE_WINDOW_SECONDS]
        if len(timestamps) >= _RATE_MAX_CALLS:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Rate limit exceeded: max {_RATE_MAX_CALLS} check executions "
                    f"per {_RATE_WINDOW_SECONDS}s per user."
                ),
            )
        timestamps.append(now)
        _rate_store[user_id] = timestamps

# Allowed check_params keys per check name.
# Only listed keys are accepted — unknown keys are rejected to prevent
# passing arbitrary constructor arguments to checker classes.
_ALLOWED_CHECK_PARAMS: dict[str, set[str]] = {
    "daily-arbel":        {"window_hours", "section_scope"},
    "daily-arbel-rds":    {"window_hours"},
    "daily-arbel-ec2":    {"window_hours"},
    "alarm_verification": {"min_duration_minutes"},
    "backup":             {"vault_mode"},
    "cost":               {"window_hours"},
    "cloudwatch":         set(),
    "guardduty":          set(),
    "notifications":      set(),
    "health":             set(),
    "ec2list":            set(),
    "ec2_utilization":    set(),
    "daily-budget":       set(),
    "huawei-ecs-util":    set(),
}

router = APIRouter(prefix="/checks", tags=["checks"])
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory job store for async execution (primary fast-path)
# Stores up to ~500 recent jobs; old entries evicted when limit is reached.
# DB persistence is a parallel write for cross-restart durability.
# ---------------------------------------------------------------------------
_MAX_JOBS = 500
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _store_job(
    job_id: str,
    status: str,
    result=None,
    error: str | None = None,
    *,
    customer_ids: list[str] | None = None,
    mode: str | None = None,
    check_name: str | None = None,
    started_at: str | None = None,
    completed_at: str | None = None,
) -> None:
    with _jobs_lock:
        if job_id in _jobs:
            # Update existing entry — merge only supplied fields
            entry = _jobs[job_id]
            entry["status"] = status
            if result is not None:
                entry["result"] = result
            if error is not None:
                entry["error"] = error
            if started_at is not None:
                entry["started_at"] = started_at
            if completed_at is not None:
                entry["completed_at"] = completed_at
        else:
            if len(_jobs) >= _MAX_JOBS:
                oldest = next(iter(_jobs))
                del _jobs[oldest]
            _jobs[job_id] = {
                "job_id": job_id,
                "status": status,
                "customer_ids": customer_ids or [],
                "mode": mode,
                "check_name": check_name,
                "started_at": started_at,
                "completed_at": completed_at,
                "result": result,
                "error": error,
                "created_at": _now_iso(),
            }


def _db_upsert_job(job_id: str, entry: dict) -> None:
    """Persist job entry to DB. Silently skips if DB is unavailable."""
    from backend.infra.database.models import CheckJob

    try:
        session = create_db_session()
        try:
            existing = session.get(CheckJob, job_id)
            if existing is None:
                existing = CheckJob(
                    id=job_id,
                    status=entry["status"],
                    customer_ids=entry.get("customer_ids") or [],
                    mode=entry.get("mode"),
                    check_name=entry.get("check_name"),
                    started_at=_parse_dt(entry.get("started_at")),
                    completed_at=_parse_dt(entry.get("completed_at")),
                    result=entry.get("result"),
                    error=entry.get("error"),
                    created_at=_parse_dt(entry.get("created_at")) or datetime.now(timezone.utc),
                )
                session.add(existing)
            else:
                existing.status = entry["status"]
                if entry.get("started_at"):
                    existing.started_at = _parse_dt(entry["started_at"])
                if entry.get("completed_at"):
                    existing.completed_at = _parse_dt(entry["completed_at"])
                if entry.get("result") is not None:
                    existing.result = entry["result"]
                if entry.get("error") is not None:
                    existing.error = entry["error"]
            session.commit()
        finally:
            session.close()
    except Exception:
        logger.debug("DB persist skipped for job %s (DB unavailable)", job_id)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _run_job(job_id: str, payload, executor) -> None:
    """Background task: execute checks and update job store."""
    started = _now_iso()
    _store_job(job_id, status="running", started_at=started)
    try:
        result = executor.execute(
            customer_ids=payload.customer_ids or [],
            mode=payload.mode,
            check_name=payload.check_name,
            account_ids=payload.account_ids,
            send_slack=payload.send_slack,
            region=payload.region,
            check_params=payload.check_params,
            run_source="api",
            persist_mode="normalized",
        )
        _store_job(
            job_id,
            status="done",
            result=result,
            completed_at=_now_iso(),
        )
    except Exception as exc:
        logger.exception("Async check job %s failed", job_id)
        _store_job(
            job_id,
            status="error",
            error=str(exc),
            completed_at=_now_iso(),
        )
    finally:
        # Persist final state to DB regardless of success/failure
        with _jobs_lock:
            entry = dict(_jobs.get(job_id, {}))
        if entry:
            _db_upsert_job(job_id, entry)


class ExecuteCheckRequest(BaseModel):
    customer_ids: list[Annotated[str, Field(min_length=1)]] | None = None
    customer_id: Annotated[str, Field(min_length=1)] | None = None
    mode: str = Field(pattern="^(single|all|arbel)$")
    check_name: str | None = None
    account_ids: list[str] | None = None
    send_slack: bool = False
    region: str | None = None
    check_params: dict[str, object] | None = None

    @field_validator("customer_ids")
    @classmethod
    def unique_customer_ids(cls, v: list[str]) -> list[str]:
        if len(v) != len(set(v)):
            raise ValueError("customer_ids must not contain duplicates")
        return v

    @field_validator("account_ids")
    @classmethod
    def validate_account_ids(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        cleaned = [item.strip() for item in v if item.strip()]
        if not cleaned:
            return None
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("account_ids must not contain duplicates")
        return cleaned

    @model_validator(mode="after")
    def validate_check_params_keys(self):
        if not self.check_params:
            return self
        check_name = self.check_name
        if not check_name:
            return self
        allowed = _ALLOWED_CHECK_PARAMS.get(check_name)
        if allowed is None:
            # Unknown check name — executor will reject it anyway
            return self
        unknown = set(self.check_params.keys()) - allowed
        if unknown:
            raise ValueError(
                f"Unknown check_params keys for '{check_name}': {sorted(unknown)}. "
                f"Allowed: {sorted(allowed) or 'none'}"
            )
        return self

    @model_validator(mode="after")
    def normalize_and_validate_compat_fields(self):
        merged_customer_ids: list[str] = []

        if self.customer_ids:
            merged_customer_ids.extend(self.customer_ids)
        if self.customer_id:
            merged_customer_ids.append(self.customer_id)

        cleaned_customer_ids = [
            item.strip() for item in merged_customer_ids if item.strip()
        ]
        if not cleaned_customer_ids:
            raise ValueError("customer_ids is required")
        if len(cleaned_customer_ids) != len(set(cleaned_customer_ids)):
            raise ValueError("customer_ids must not contain duplicates")

        self.customer_ids = cleaned_customer_ids

        return self


class CheckRunResponse(BaseModel):
    customer_id: str
    check_run_id: str
    slack_sent: bool


class AccountResponse(BaseModel):
    id: str
    profile_name: str
    display_name: str


class CheckResultResponse(BaseModel):
    customer_id: str
    account: AccountResponse
    check_name: str
    status: str
    summary: str
    output: str
    details: dict | None = None
    error_class: str | None = None


class ExecuteCheckResponse(BaseModel):
    check_runs: list[CheckRunResponse]
    execution_time_seconds: float
    results: list[CheckResultResponse]
    consolidated_outputs: dict[str, str]
    customer_labels: dict[str, str] = Field(default_factory=dict)
    backup_overviews: dict[str, dict[str, object]] = Field(default_factory=dict)
    check_run_id: str | None = None
    consolidated_output: str | None = None


class AvailableCheckItem(BaseModel):
    name: str
    class_: str = Field(alias="class")


class AvailableChecksResponse(BaseModel):
    checks: list[AvailableCheckItem]


@router.post("/execute", response_model=ExecuteCheckResponse)
def execute_check(
    payload: ExecuteCheckRequest,
    request: Request,
    executor=Depends(get_check_executor),
    _auth=Depends(require_auth),
):
    user_id = getattr(request.state, "auth_user", None)
    _check_rate_limit(getattr(user_id, "user_id", "anonymous"))

    try:
        if payload.mode == "single" and not payload.check_name:
            raise HTTPException(
                status_code=400, detail="check_name required for single mode"
            )

        result = executor.execute(
            customer_ids=payload.customer_ids or [],
            mode=payload.mode,
            check_name=payload.check_name,
            account_ids=payload.account_ids,
            send_slack=payload.send_slack,
            region=payload.region,
            check_params=payload.check_params,
            run_source="api",
            persist_mode="normalized",
        )

        if not result.get("check_run_id"):
            check_runs = result.get("check_runs") or []
            if check_runs:
                result["check_run_id"] = check_runs[0].get("check_run_id")

        if not result.get("consolidated_output"):
            consolidated_outputs = result.get("consolidated_outputs") or {}
            if isinstance(consolidated_outputs, dict) and consolidated_outputs:
                result["consolidated_output"] = next(
                    iter(consolidated_outputs.values())
                )

        return ExecuteCheckResponse.model_validate(result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Check execution failed")
        raise HTTPException(status_code=500, detail=f"Execution failed: {exc}") from exc


@router.post("/execute/async")
async def execute_check_async(
    payload: ExecuteCheckRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    executor=Depends(get_check_executor),
    _auth=Depends(require_auth),
):
    """Queue a check execution and return a job_id immediately.

    Poll GET /checks/jobs/{job_id} to retrieve the result when status == "done".
    Use this for large multi-customer / all-mode runs to avoid HTTP timeouts.
    """
    user_id = getattr(request.state, "auth_user", None)
    _check_rate_limit(getattr(user_id, "user_id", "anonymous"))

    if payload.mode == "single" and not payload.check_name:
        raise HTTPException(
            status_code=400, detail="check_name required for single mode"
        )

    job_id = str(uuid4())
    _store_job(
        job_id,
        status="queued",
        customer_ids=payload.customer_ids or [],
        mode=payload.mode,
        check_name=payload.check_name,
    )
    background_tasks.add_task(_run_job, job_id, payload, executor)
    return {"job_id": job_id, "status": "queued"}


@router.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    """Poll the status of an async check job.

    Returns:
        status: "queued" | "running" | "done" | "error"
        result: ExecuteCheckResponse payload (when status == "done")
        error: error message (when status == "error")

    In-memory is checked first (fast path for active jobs).
    Falls back to DB for completed jobs that survived a server restart.
    """
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is not None:
        return job

    # Fallback: try DB
    try:
        from backend.infra.database.models import CheckJob

        session = create_db_session()
        try:
            db_job = session.get(CheckJob, job_id)
        finally:
            session.close()
        if db_job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return _db_job_to_dict(db_job)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=404, detail="Job not found")


def _db_job_to_dict(db_job) -> dict:
    return {
        "job_id": db_job.id,
        "status": db_job.status,
        "customer_ids": db_job.customer_ids or [],
        "mode": db_job.mode,
        "check_name": db_job.check_name,
        "started_at": db_job.started_at.isoformat() if db_job.started_at else None,
        "completed_at": db_job.completed_at.isoformat() if db_job.completed_at else None,
        "created_at": db_job.created_at.isoformat() if db_job.created_at else None,
        "result": db_job.result,
        "error": db_job.error,
    }


@router.get("/jobs")
def list_jobs():
    """Return last 100 check jobs (most recent first), without result/details payload.

    Merges in-memory (active) jobs with DB (historical) jobs.
    Each item: job_id, status, customer_ids, mode, check_name,
                started_at, completed_at, created_at, error
    """
    with _jobs_lock:
        mem_jobs = {jid: dict(j) for jid, j in _jobs.items()}

    # Fetch from DB (historical + completed jobs)
    db_jobs: dict[str, dict] = {}
    try:
        from backend.infra.database.models import CheckJob
        from sqlalchemy import desc

        session = create_db_session()
        try:
            rows = (
                session.query(CheckJob)
                .order_by(desc(CheckJob.created_at))
                .limit(200)
                .all()
            )
            for row in rows:
                db_jobs[row.id] = _db_job_to_dict(row)
        finally:
            session.close()
    except Exception:
        pass  # DB unavailable — serve in-memory only

    # Merge: in-memory takes priority (has live status for active jobs)
    merged: dict[str, dict] = {**db_jobs, **mem_jobs}

    # Sort by created_at descending, limit 100, strip result payload
    sorted_jobs = sorted(
        merged.values(),
        key=lambda j: j.get("created_at") or "",
        reverse=True,
    )[:100]

    return [{k: v for k, v in job.items() if k != "result"} for job in sorted_jobs]


@router.get("/available", response_model=AvailableChecksResponse)
def list_available_checks():
    """Return list of available check types."""
    from backend.domain.runtime.config import AVAILABLE_CHECKS

    return {
        "checks": [
            {
                "name": name,
                "class": getattr(cls, "__name__", getattr(cls, "func", cls).__name__),
            }
            for name, cls in AVAILABLE_CHECKS.items()
        ]
    }
