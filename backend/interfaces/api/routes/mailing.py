"""Mailing contacts endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, field_validator

from backend.infra.database.repositories.mailing_repository import MailingRepository
from backend.interfaces.api.dependencies import _get_session

router = APIRouter(prefix="/mailing", tags=["mailing"])


def _get_repo():
    session = _get_session()
    try:
        yield MailingRepository(session)
    finally:
        session.close()


class MailingContactResponse(BaseModel):
    id: str
    customer_id: str | None = None
    email: str
    name: str | None = None
    created_at: str


class CreateContactRequest(BaseModel):
    customer_id: str | None = None
    email: str
    name: str | None = None

    @field_validator("email")
    @classmethod
    def valid_email(cls, v: str) -> str:
        v = v.strip()
        if not v or "@" not in v:
            raise ValueError("email tidak valid")
        return v


def _to_response(row) -> MailingContactResponse:
    return MailingContactResponse(
        id=row.id,
        customer_id=row.customer_id,
        email=row.email,
        name=row.name,
        created_at=row.created_at.isoformat(),
    )


@router.get("", response_model=list[MailingContactResponse])
def list_contacts(
    customer_id: str | None = Query(default=None),
    repo: Annotated[MailingRepository, Depends(_get_repo)] = None,
):
    return [_to_response(c) for c in repo.list_contacts(customer_id=customer_id)]


@router.post("", response_model=MailingContactResponse, status_code=status.HTTP_201_CREATED)
def create_contact(
    body: CreateContactRequest,
    repo: Annotated[MailingRepository, Depends(_get_repo)],
):
    row = repo.create_contact(
        customer_id=body.customer_id,
        email=body.email,
        name=body.name,
    )
    repo.session.commit()
    return _to_response(row)


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(
    contact_id: str,
    repo: Annotated[MailingRepository, Depends(_get_repo)],
):
    contact = repo.get_contact(contact_id)
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    repo.session.delete(contact)
    repo.session.commit()
