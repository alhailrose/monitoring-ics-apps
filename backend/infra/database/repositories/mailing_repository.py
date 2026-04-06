"""Repository for mailing contact persistence."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.infra.database.models import MailingContact


class MailingRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_contacts(self, customer_id: str | None = None) -> list[MailingContact]:
        stmt = select(MailingContact).order_by(MailingContact.created_at)
        if customer_id:
            stmt = stmt.where(MailingContact.customer_id == customer_id)
        return list(self.session.execute(stmt).scalars().all())

    def get_contact(self, contact_id: str) -> MailingContact | None:
        return self.session.execute(
            select(MailingContact).where(MailingContact.id == contact_id)
        ).scalar_one_or_none()

    def create_contact(
        self,
        *,
        customer_id: str | None,
        email: str,
        name: str | None,
    ) -> MailingContact:
        contact = MailingContact(
            customer_id=customer_id,
            email=email,
            name=name,
        )
        self.session.add(contact)
        self.session.flush()
        self.session.refresh(contact)
        return contact
