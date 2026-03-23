"""Metric sample query endpoints."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from backend.interfaces.api.dependencies import get_check_repository

router = APIRouter(prefix="/metrics", tags=["metrics"])


class MetricAccountResponse(BaseModel):
    id: str
    profile_name: str
    display_name: str


class MetricCustomerResponse(BaseModel):
    id: str
    display_name: str


class MetricItemResponse(BaseModel):
    id: str
    check_run_id: str
    customer: MetricCustomerResponse
    account: MetricAccountResponse
    check_name: str
    metric_name: str
    metric_status: str
    value_num: float | None = None
    unit: str | None = None
    resource_role: str | None = None
    resource_id: str | None = None
    resource_name: str | None = None
    service_type: str | None = None
    section_name: str | None = None
    created_at: str


class MetricListResponse(BaseModel):
    total: int
    items: list[MetricItemResponse]


class MetricTimeseriesItem(BaseModel):
    date: str
    metric_name: str
    account_id: str
    account_display_name: str
    avg_value: float | None = None
    max_value: float | None = None
    sample_count: int


class MetricTimeseriesResponse(BaseModel):
    items: list[MetricTimeseriesItem]


@router.get("/timeseries", response_model=MetricTimeseriesResponse)
def get_metric_timeseries(
    check_name: str = Query(...),
    customer_id: str | None = Query(None),
    account_id: str | None = Query(None),
    days: int = Query(14, ge=1, le=90),
    repo=Depends(get_check_repository),
):
    items = repo.get_metric_timeseries(
        check_name=check_name,
        customer_id=customer_id,
        account_id=account_id,
        days=days,
    )
    return {"items": items}


@router.get("", response_model=MetricListResponse)
def list_metrics(
    customer_id: str | None = Query(None),
    check_name: str | None = Query(None),
    metric_name: str | None = Query(None),
    metric_status: str | None = Query(None),
    account_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    repo=Depends(get_check_repository),
):
    samples, total = repo.list_metric_samples(
        customer_id=customer_id,
        check_name=check_name,
        metric_name=metric_name,
        metric_status=metric_status,
        account_id=account_id,
        limit=limit,
        offset=offset,
    )

    items = []
    for sample in samples:
        account = sample.account
        items.append(
            {
                "id": sample.id,
                "check_run_id": sample.check_run_id,
                "customer": {
                    "id": account.customer.id,
                    "display_name": account.customer.display_name,
                },
                "account": {
                    "id": account.id,
                    "profile_name": account.profile_name,
                    "display_name": account.display_name,
                },
                "check_name": sample.check_name,
                "metric_name": sample.metric_name,
                "metric_status": sample.metric_status,
                "value_num": sample.value_num,
                "unit": sample.unit,
                "resource_role": sample.resource_role,
                "resource_id": sample.resource_id,
                "resource_name": sample.resource_name,
                "service_type": sample.service_type,
                "section_name": sample.section_name,
                "created_at": sample.created_at.isoformat(),
            }
        )

    return {"total": total, "items": items}
