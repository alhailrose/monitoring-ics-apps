"""Repository for invite persistence."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.infra.database.models import Invite


class InviteRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, email: str, token: str, role: str, invited_by: str, expires_at: datetime) -> Invite:
        invite = Invite(
            email=email,
            token=token,
            role=role,
            invited_by=invited_by,
            expires_at=expires_at,
        )
        self.session.add(invite)
        self.session.flush()
        self.session.refresh(invite)
        return invite

    def get_by_token(self, token: str) -> Invite | None:
        return self.session.execute(
            select(Invite).where(Invite.token == token)
        ).scalar_one_or_none()

    def get_pending_by_email(self, email: str) -> Invite | None:
        now = datetime.now(timezone.utc)
        return self.session.execute(
            select(Invite).where(
                Invite.email == email,
                Invite.accepted == False,  # noqa: E712
                Invite.expires_at > now,
            )
        ).scalar_one_or_none()

    def mark_accepted(self, token: str) -> Invite | None:
        invite = self.get_by_token(token)
        if invite:
            invite.accepted = True
            self.session.flush()
        return invite

    def list_all(self) -> list[Invite]:
        return list(self.session.execute(select(Invite).order_by(Invite.created_at.desc())).scalars().all())
