"""Findings query endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from backend.interfaces.api.dependencies import get_check_repository

router = APIRouter(prefix="/findings", tags=["findings"])


class FindingAccountResponse(BaseModel):
    id: str
    profile_name: str
    display_name: str


class FindingCustomerResponse(BaseModel):
    id: str
    display_name: str


class FindingItemResponse(BaseModel):
    id: str
    check_run_id: str
    customer: FindingCustomerResponse
    account: FindingAccountResponse
    check_name: str
    finding_key: str
    severity: str
    title: str
    description: str | None = None
    created_at: str


class FindingsListResponse(BaseModel):
    total: int
    items: list[FindingItemResponse]


@router.get("", response_model=FindingsListResponse)
def list_findings(
    customer_id: str | None = Query(None),
    check_name: str | None = Query(None),
    severity: str | None = Query(None),
    account_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    repo=Depends(get_check_repository),
):
    findings, total = repo.list_findings(
        customer_id=customer_id,
        check_name=check_name,
        severity=severity,
        account_id=account_id,
        limit=limit,
        offset=offset,
    )

    items = []
    for finding in findings:
        account = finding.account
        items.append(
            {
                "id": finding.id,
                "check_run_id": finding.check_run_id,
                "customer": {
                    "id": account.customer.id,
                    "display_name": account.customer.display_name,
                },
                "account": {
                    "id": account.id,
                    "profile_name": account.profile_name,
                    "display_name": account.display_name,
                },
                "check_name": finding.check_name,
                "finding_key": finding.finding_key,
                "severity": finding.severity,
                "title": finding.title,
                "description": finding.description,
                "created_at": finding.created_at.isoformat(),
            }
        )

    return {"total": total, "items": items}
