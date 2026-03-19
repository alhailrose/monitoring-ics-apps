"""Dashboard summary endpoints."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from backend.interfaces.api.dependencies import get_check_repository

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class DashboardRunsResponse(BaseModel):
    total: int
    single: int
    all: int
    arbel: int
    latest_created_at: str | None = None


class DashboardResultsResponse(BaseModel):
    total: int
    ok: int
    warn: int
    error: int
    alarm: int
    no_data: int


class DashboardFindingsResponse(BaseModel):
    total: int
    by_severity: dict[str, int]


class DashboardMetricsResponse(BaseModel):
    total: int
    by_status: dict[str, int]


class DashboardTopCheckItem(BaseModel):
    check_name: str
    runs: int


class DashboardSummaryResponse(BaseModel):
    customer_id: str
    window_hours: int
    generated_at: str
    since: str
    runs: DashboardRunsResponse
    results: DashboardResultsResponse
    findings: DashboardFindingsResponse
    metrics: DashboardMetricsResponse
    top_checks: list[DashboardTopCheckItem]


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    customer_id: str,
    window_hours: int = Query(24, ge=1, le=720),
    repo=Depends(get_check_repository),
):
    summary = repo.get_dashboard_summary(
        customer_id=customer_id,
        window_hours=window_hours,
    )

    runs = dict(summary["runs"])
    latest_created_at = runs.get("latest_created_at")
    runs["latest_created_at"] = (
        latest_created_at.isoformat() if latest_created_at else None
    )

    return {
        "customer_id": summary["customer_id"],
        "window_hours": summary["window_hours"],
        "generated_at": summary["generated_at"].isoformat(),
        "since": summary["since"].isoformat(),
        "runs": runs,
        "results": summary["results"],
        "findings": summary["findings"],
        "metrics": summary["metrics"],
        "top_checks": summary["top_checks"],
    }
