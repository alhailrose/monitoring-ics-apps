"""Check execution endpoints."""

from typing import Annotated
import logging
import threading
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator

from backend.interfaces.api.dependencies import get_check_executor

router = APIRouter(prefix="/checks", tags=["checks"])
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory job store for async execution
# Stores up to ~500 recent jobs; old entries evicted when limit is reached.
# ---------------------------------------------------------------------------
_MAX_JOBS = 500
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()


def _store_job(job_id: str, status: str, result=None, error: str | None = None) -> None:
    with _jobs_lock:
        if len(_jobs) >= _MAX_JOBS:
            oldest = next(iter(_jobs))
            del _jobs[oldest]
        _jobs[job_id] = {
            "job_id": job_id,
            "status": status,
            "result": result,
            "error": error,
        }


def _run_job(job_id: str, payload, executor) -> None:
    """Background task: execute checks and update job store."""
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
        _store_job(job_id, status="done", result=result)
    except Exception as exc:
        logger.exception("Async check job %s failed", job_id)
        _store_job(job_id, status="error", error=str(exc))


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
def execute_check(payload: ExecuteCheckRequest, executor=Depends(get_check_executor)):
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
    background_tasks: BackgroundTasks,
    executor=Depends(get_check_executor),
):
    """Queue a check execution and return a job_id immediately.

    Poll GET /checks/jobs/{job_id} to retrieve the result when status == "done".
    Use this for large multi-customer / all-mode runs to avoid HTTP timeouts.
    """
    if payload.mode == "single" and not payload.check_name:
        raise HTTPException(
            status_code=400, detail="check_name required for single mode"
        )

    job_id = str(uuid4())
    _store_job(job_id, status="queued")
    background_tasks.add_task(_run_job, job_id, payload, executor)
    return {"job_id": job_id, "status": "queued"}


@router.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    """Poll the status of an async check job.

    Returns:
        status: "queued" | "done" | "error"
        result: ExecuteCheckResponse payload (when status == "done")
        error: error message (when status == "error")
    """
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


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
