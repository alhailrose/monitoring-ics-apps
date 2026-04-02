"""add google auth columns and invites table

Revision ID: a1b2c3d4e5f6
Revises: 9b4de82e1b11
Create Date: 2026-04-02 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "9b4de82e1b11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add Google auth columns to users
    op.add_column("users", sa.Column("email", sa.String(256), nullable=True))
    op.add_column("users", sa.Column("google_sub", sa.String(256), nullable=True))
    op.add_column("users", sa.Column("auth_provider", sa.String(32), nullable=False, server_default="password"))
    op.alter_column("users", "hashed_password", nullable=True)

    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_google_sub", "users", ["google_sub"], unique=True)

    # Create invites table
    op.create_table(
        "invites",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(256), nullable=False),
        sa.Column("token", sa.String(128), nullable=False, unique=True),
        sa.Column("role", sa.String(32), nullable=False, server_default="user"),
        sa.Column("invited_by", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("accepted", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_invites_email", "invites", ["email"])
    op.create_index("ix_invites_token", "invites", ["token"], unique=True)


def downgrade() -> None:
    op.drop_table("invites")
    op.drop_index("ix_users_google_sub", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_column("users", "auth_provider")
    op.drop_column("users", "google_sub")
    op.drop_column("users", "email")
    op.alter_column("users", "hashed_password", nullable=False)
