"""Check execution endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from src.app.api.dependencies import get_check_executor

router = APIRouter(prefix="/checks", tags=["checks"])


class ExecuteCheckRequest(BaseModel):
    customer_ids: list[Annotated[str, Field(min_length=1)]] = Field(min_length=1)
    mode: str = Field(pattern="^(single|all|arbel)$")
    check_name: str | None = None
    account_ids: list[str] | None = None
    send_slack: bool = False
    region: str | None = None
    check_params: dict | None = None  # Extra params passed to checker (e.g. window_hours, alarm_names)

    @field_validator("customer_ids")
    @classmethod
    def unique_customer_ids(cls, v: list[str]) -> list[str]:
        if len(v) != len(set(v)):
            raise ValueError("customer_ids must not contain duplicates")
        return v


@router.post("/execute")
def execute_check(payload: ExecuteCheckRequest, executor=Depends(get_check_executor)):
    try:
        result = executor.execute(
            customer_ids=payload.customer_ids,
            mode=payload.mode,
            check_name=payload.check_name,
            account_ids=payload.account_ids,
            send_slack=payload.send_slack,
            region=payload.region,
            check_params=payload.check_params,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Execution failed: {exc}")


@router.get("/available")
def list_available_checks():
    """Return list of available check types."""
    from src.core.runtime.config import AVAILABLE_CHECKS
    return {
        "checks": [
            {"name": name, "class": cls.__name__}
            for name, cls in AVAILABLE_CHECKS.items()
        ]
    }
