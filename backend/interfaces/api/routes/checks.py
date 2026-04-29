"""Check execution endpoints."""

from typing import Annotated
import logging
import threading
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator, model_validator

from backend.interfaces.api.dependencies import (
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
    "daily-arbel": {"window_hours", "section_scope"},
    "daily-arbel-rds": {"window_hours"},
    "daily-arbel-ec2": {"window_hours"},
    "alarm_verification": {"min_duration_minutes"},
    "backup": {"vault_mode"},
    "cost": {"window_hours"},
    "cloudwatch": set(),
    "guardduty": set(),
    "notifications": set(),
    "health": set(),
    "ec2list": set(),
    "ec2_utilization": set(),
    "daily-budget": set(),
    "huawei-ecs-util": set(),
}

router = APIRouter(prefix="/checks", tags=["checks"])
logger = logging.getLogger(__name__)


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
