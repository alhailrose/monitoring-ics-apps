"""Check execution endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.app.api.dependencies import get_check_executor

router = APIRouter(prefix="/checks", tags=["checks"])


class ExecuteCheckRequest(BaseModel):
    customer_id: str
    mode: str = Field(pattern="^(single|all|arbel)$")
    check_name: str | None = None
    account_ids: list[str] | None = None
    send_slack: bool = False
    region: str | None = None


@router.post("/execute")
def execute_check(payload: ExecuteCheckRequest, executor=Depends(get_check_executor)):
    try:
        result = executor.execute(
            customer_id=payload.customer_id,
            mode=payload.mode,
            check_name=payload.check_name,
            account_ids=payload.account_ids,
            send_slack=payload.send_slack,
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
