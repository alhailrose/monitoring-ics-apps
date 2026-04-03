"""Repository for ticket persistence."""

from __future__ import annotations

import re

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from backend.infra.database.models import Ticket


class TicketRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_tickets(self) -> list[Ticket]:
        stmt = select(Ticket).order_by(desc(Ticket.created_at))
        return list(self.session.execute(stmt).scalars().all())

    def get_ticket(self, ticket_id: str) -> Ticket | None:
        stmt = select(Ticket).where(Ticket.id == ticket_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def next_ticket_number(self) -> str:
        stmt = select(Ticket.ticket_no).order_by(desc(Ticket.created_at)).limit(1)
        latest = self.session.execute(stmt).scalar_one_or_none()
        if not latest:
            return "TKT-0001"

        match = re.search(r"(\d+)$", latest)
        next_no = 1 if not match else int(match.group(1)) + 1
        return f"TKT-{next_no:04d}"

    def create_ticket(
        self,
        *,
        ticket_no: str,
        task: str,
        pic: str,
        status: str,
        description_solution: str | None,
        ended_at=None,
    ) -> Ticket:
        ticket = Ticket(
            ticket_no=ticket_no,
            task=task,
            pic=pic,
            status=status,
            description_solution=description_solution,
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
