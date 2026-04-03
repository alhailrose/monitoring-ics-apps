"""Invite service — create and accept user invites."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from backend.infra.database.models import Invite, User
from backend.infra.database.repositories.invite_repository import InviteRepository
from backend.infra.database.repositories.user_repository import UserRepository
from backend.infra.notifications.email_sender import send_invite_email

_ALLOWED_DOMAIN = "icscompute.com"


class InviteError(Exception):
    pass


class InviteService:
    def __init__(
        self,
        invite_repo: InviteRepository,
        user_repo: UserRepository,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        smtp_from: str,
        app_base_url: str,
        invite_expire_hours: int,
    ):
        self._invites = invite_repo
        self._users = user_repo
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._smtp_user = smtp_user
        self._smtp_password = smtp_password
        self._smtp_from = smtp_from
        self._app_base_url = app_base_url.rstrip("/")
        self._expire_hours = invite_expire_hours

    def create_invite(self, email: str, role: str, invited_by: User) -> Invite:
        email = email.strip().lower()
        if not email.endswith(f"@{_ALLOWED_DOMAIN}"):
            raise InviteError(f"Only @{_ALLOWED_DOMAIN} email addresses can be invited")

        # Check no pending invite already exists
        existing = self._invites.get_pending_by_email(email)
        if existing:
            raise InviteError(f"A pending invite already exists for {email}")

        # Check user doesn't already exist
        if self._users.get_by_email(email):
            raise InviteError(f"User with email {email} already exists")

        inviter_id = getattr(invited_by, "id", None) or getattr(
            invited_by, "user_id", None
        )
        inviter_username = getattr(invited_by, "username", None)
        if not inviter_id or not inviter_username:
            raise InviteError("Invalid inviter context")

        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=self._expire_hours)
        invite = self._invites.create(
            email=email,
            token=token,
            role=role,
            invited_by=inviter_id,
            expires_at=expires_at,
        )

        invite_url = f"{self._app_base_url}/auth/google?invite={token}"
        send_invite_email(
            to_email=email,
            invite_url=invite_url,
            invited_by_username=inviter_username,
            smtp_host=self._smtp_host,
            smtp_port=self._smtp_port,
            smtp_user=self._smtp_user,
            smtp_password=self._smtp_password,
            smtp_from=self._smtp_from,
        )
        self._invites.session.commit()
        return invite

    def accept_invite(self, token: str, google_sub: str, email: str) -> User:
        """Accept an invite and create the user account. Returns the new User."""
        invite = self._invites.get_by_token(token)
        now = datetime.now(timezone.utc)

        if not invite:
            raise InviteError("Invalid invite token")
        if invite.accepted:
            raise InviteError("Invite already used")
        if invite.expires_at.replace(tzinfo=timezone.utc) < now:
            raise InviteError("Invite has expired")
        if invite.email.lower() != email.lower():
            raise InviteError("Google account email does not match invite")

        # Derive username from email local part
        username = email.split("@")[0].replace(".", "_").lower()
        # Make unique if already taken
        base = username
        counter = 1
        while self._users.get_by_username(username):
            username = f"{base}_{counter}"
            counter += 1

        user = self._users.create_google_user(
            email=email,
            google_sub=google_sub,
            username=username,
            role=invite.role,
        )
        self._invites.mark_accepted(token)
        return user
