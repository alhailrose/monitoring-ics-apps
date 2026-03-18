"""Check execution endpoints."""

from typing import Annotated
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator

from src.app.api.dependencies import get_check_executor

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

        if self.mode == "single" and not self.check_name:
            raise ValueError("check_name required for single mode")

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


class ExecuteCheckResponse(BaseModel):
    check_runs: list[CheckRunResponse]
    execution_time_seconds: float
    results: list[CheckResultResponse]
    consolidated_outputs: dict[str, str]
    backup_overviews: dict[str, dict[str, object]] = Field(default_factory=dict)


class AvailableCheckItem(BaseModel):
    name: str
    class_: str = Field(alias="class")


class AvailableChecksResponse(BaseModel):
    checks: list[AvailableCheckItem]


@router.post("/execute", response_model=ExecuteCheckResponse)
def execute_check(payload: ExecuteCheckRequest, executor=Depends(get_check_executor)):
    try:
        result = executor.execute(
            customer_ids=payload.customer_ids or [],
            mode=payload.mode,
            check_name=payload.check_name,
            account_ids=payload.account_ids,
            send_slack=payload.send_slack,
            region=payload.region,
            check_params=payload.check_params,
        )
        return ExecuteCheckResponse.model_validate(result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Check execution failed")
        raise HTTPException(status_code=500, detail="Execution failed") from exc


@router.get("/available", response_model=AvailableChecksResponse)
def list_available_checks():
    """Return list of available check types."""
    from src.core.runtime.config import AVAILABLE_CHECKS

    return {
        "checks": [
            {"name": name, "class": cls.__name__}
            for name, cls in AVAILABLE_CHECKS.items()
        ]
    }
