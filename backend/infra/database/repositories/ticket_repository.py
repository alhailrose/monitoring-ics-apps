"""Repository for ticket persistence."""

from __future__ import annotations

from sqlalchemy import desc, extract, select
from sqlalchemy.orm import Session

from backend.infra.database.models import Ticket


class TicketRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_tickets(
        self,
        customer_id: str | None = None,
        month: int | None = None,
        year: int | None = None,
    ) -> list[Ticket]:
        stmt = select(Ticket).order_by(desc(Ticket.created_at))
        if customer_id:
            stmt = stmt.where(Ticket.customer_id == customer_id)
        if month:
            stmt = stmt.where(extract("month", Ticket.created_at) == month)
        if year:
            stmt = stmt.where(extract("year", Ticket.created_at) == year)
        return list(self.session.execute(stmt).scalars().all())

    def get_ticket(self, ticket_id: str) -> Ticket | None:
        stmt = select(Ticket).where(Ticket.id == ticket_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def create_ticket(
        self,
        *,
        ticket_no: str | None = None,
        customer_id: str | None,
        task: str,
        pic: str,
        status: str,
        description_solution: str | None,
        extra_data: dict | None = None,
        ended_at=None,
    ) -> Ticket:
        ticket = Ticket(
            ticket_no=ticket_no or None,
            customer_id=customer_id,
            task=task,
            pic=pic,
            status=status,
            description_solution=description_solution,
            extra_data=extra_data,
            ended_at=ended_at,
        )
        self.session.add(ticket)
        self.session.flush()
        self.session.refresh(ticket)
        return ticket

    def update_ticket(self, ticket_id: str, **kwargs) -> Ticket | None:
        ticket = self.get_ticket(ticket_id)
        if ticket is None:
            return None
        for key, value in kwargs.items():
            if hasattr(ticket, key):
                setattr(ticket, key, value)
        self.session.flush()
        return ticket
