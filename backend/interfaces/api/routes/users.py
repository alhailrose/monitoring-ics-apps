"""User management endpoints — only accessible by super_user role."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from backend.domain.services.auth_service import hash_password
from backend.infra.database.repositories.user_repository import UserRepository
from backend.interfaces.api.dependencies import require_role, _get_session

router = APIRouter(prefix="/users", tags=["users"])

_super_user = Depends(require_role("super_user"))


# ── Schemas ───────────────────────────────────────────────────────────────────


class UserResponse(BaseModel):
    id: str
    username: str
    role: str
    is_active: bool


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "user"

    @field_validator("role")
    @classmethod
    def valid_role(cls, v: str) -> str:
        if v not in ("user", "super_user"):
            raise ValueError("role must be 'user' or 'super_user'")
        return v

    @field_validator("password")
    @classmethod
    def min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v


class UpdateRoleRequest(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def valid_role(cls, v: str) -> str:
        if v not in ("user", "super_user"):
            raise ValueError("role must be 'user' or 'super_user'")
        return v


# ── Dependency ────────────────────────────────────────────────────────────────


def _get_repo():
    session = _get_session()
    try:
        yield UserRepository(session)
    finally:
        session.close()


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("", response_model=list[UserResponse], dependencies=[_super_user])
def list_users(repo: Annotated[UserRepository, Depends(_get_repo)]):
    """List all users."""
    return [
        UserResponse(
            id=str(u.id), username=u.username, role=u.role, is_active=u.is_active
        )
        for u in repo.list_users()
    ]


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_super_user],
)
def create_user(
    body: CreateUserRequest, repo: Annotated[UserRepository, Depends(_get_repo)]
):
    """Create a new user."""
    if repo.get_by_username(body.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username already exists"
        )
    user = repo.create_user(
        username=body.username,
        hashed_password=hash_password(body.password),
        role=body.role,
    )
    repo.session.commit()
    return UserResponse(
        id=str(user.id),
        username=user.username,
        role=user.role,
        is_active=user.is_active,
    )


@router.patch(
    "/{user_id}/role", response_model=UserResponse, dependencies=[_super_user]
)
def update_role(
    user_id: str,
    body: UpdateRoleRequest,
    repo: Annotated[UserRepository, Depends(_get_repo)],
):
    """Update a user's role."""
    user = repo.update_role(user_id, body.role)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    repo.session.commit()
    return UserResponse(
        id=str(user.id),
        username=user.username,
        role=user.role,
        is_active=user.is_active,
    )


@router.delete(
    "/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[_super_user]
)
def deactivate_user(user_id: str, repo: Annotated[UserRepository, Depends(_get_repo)]):
    """Deactivate a user (soft delete)."""
    user = repo.deactivate(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    repo.session.commit()
