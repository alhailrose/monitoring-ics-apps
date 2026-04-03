"""Ticketing endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from backend.infra.database.repositories.ticket_repository import TicketRepository
from backend.interfaces.api.dependencies import _get_session

router = APIRouter(prefix="/tickets", tags=["tickets"])

_FINAL_STATUSES = {"resolved", "closed"}


class TicketResponse(BaseModel):
    id: str
    ticket_no: str
    customer_id: str | None = None
    task: str
    pic: str
    status: str
    description_solution: str | None = None
    created_at: str
    ended_at: str | None = None


class CreateTicketRequest(BaseModel):
    customer_id: str
    task: str
    pic: str
    status: str = "open"
    description_solution: str | None = None

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str) -> str:
        if value not in {"open", "in_progress", "resolved", "closed"}:
            raise ValueError(
                "status must be one of: open, in_progress, resolved, closed"
            )
        return value

    @field_validator("customer_id")
    @classmethod
    def valid_customer_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("customer_id is required")
        return cleaned


class UpdateTicketRequest(BaseModel):
    customer_id: str | None = None
    task: str | None = None
    pic: str | None = None
    status: str | None = None
    description_solution: str | None = None

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if value not in {"open", "in_progress", "resolved", "closed"}:
            raise ValueError(
                "status must be one of: open, in_progress, resolved, closed"
            )
        return value

    @field_validator("customer_id")
    @classmethod
    def valid_optional_customer_id(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("customer_id must not be blank")
        return cleaned


def _to_response(row) -> TicketResponse:
    return TicketResponse(
        id=row.id,
        ticket_no=row.ticket_no,
        customer_id=row.customer_id,
        task=row.task,
        pic=row.pic,
        status=row.status,
        description_solution=row.description_solution,
        created_at=row.created_at.isoformat(),
        ended_at=row.ended_at.isoformat() if row.ended_at else None,
    )


def _get_repo():
    session = _get_session()
    try:
        yield TicketRepository(session)
    finally:
        session.close()


@router.get("", response_model=list[TicketResponse])
def list_tickets(repo: Annotated[TicketRepository, Depends(_get_repo)]):
    return [_to_response(row) for row in repo.list_tickets()]


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(
    body: CreateTicketRequest,
    repo: Annotated[TicketRepository, Depends(_get_repo)],
):
    ended_at = datetime.now(timezone.utc) if body.status in _FINAL_STATUSES else None
    row = repo.create_ticket(
        ticket_no=repo.next_ticket_number(),
        customer_id=body.customer_id,
        task=body.task,
        pic=body.pic,
        status=body.status,
        description_solution=body.description_solution,
        ended_at=ended_at,
    )
    repo.session.commit()
    return _to_response(row)


@router.patch("/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    ticket_id: str,
    body: UpdateTicketRequest,
    repo: Annotated[TicketRepository, Depends(_get_repo)],
):
    existing = repo.get_ticket(ticket_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    updates: dict[str, object] = {}
    if body.customer_id is not None:
        updates["customer_id"] = body.customer_id
    if body.task is not None:
        updates["task"] = body.task
    if body.pic is not None:
        updates["pic"] = body.pic
    if body.description_solution is not None:
        updates["description_solution"] = body.description_solution
    if body.status is not None:
        updates["status"] = body.status
        if body.status in _FINAL_STATUSES:
            updates["ended_at"] = existing.ended_at or datetime.now(timezone.utc)
        else:
            updates["ended_at"] = None

    row = repo.update_ticket(ticket_id, **updates)
    if row is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    repo.session.commit()
    return _to_response(row)
