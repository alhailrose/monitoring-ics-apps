"""Repository for user persistence."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.infra.database.models import User


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, user_id: str) -> User | None:
        return self.session.execute(
            select(User).where(User.id == user_id)
        ).scalar_one_or_none()

    def get_by_username(self, username: str) -> User | None:
        return self.session.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()

    def create_user(self, username: str, hashed_password: str, role: str = "user") -> User:
        user = User(username=username, hashed_password=hashed_password, role=role)
        self.session.add(user)
        self.session.flush()
        self.session.refresh(user)
        return user

    def list_users(self) -> list[User]:
        return list(self.session.execute(select(User)).scalars().all())

    def update_role(self, user_id: str, role: str) -> User | None:
        user = self.get_by_id(user_id)
        if user:
            user.role = role
            self.session.flush()
        return user

    def deactivate(self, user_id: str) -> User | None:
        user = self.get_by_id(user_id)
        if user:
            user.is_active = False
            self.session.flush()
        return user
