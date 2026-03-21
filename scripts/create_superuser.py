"""Seed an initial super_user account if none exists.

Usage:
    python -m scripts.create_superuser

Environment variables:
    DATABASE_URL       — PostgreSQL connection string (defaults to local dev URL)
    SUPERUSER_USERNAME — Username for the super_user (default: admin)
    SUPERUSER_PASSWORD — Password for the super_user (required if not prompted)

If SUPERUSER_PASSWORD is not set, the script will prompt interactively.
"""

import getpass
import os
import sys

from sqlalchemy import select

from backend.config.settings import get_settings
from backend.domain.services.auth_service import hash_password
from backend.infra.database.models import User
from backend.infra.database.session import build_session_factory


def main() -> None:
    settings = get_settings()
    session_factory = build_session_factory(settings.database_url)

    username = os.getenv("SUPERUSER_USERNAME", "admin")
    password = os.getenv("SUPERUSER_PASSWORD")

    if not password:
        password = getpass.getpass(f"Password for '{username}': ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords do not match. Aborting.")
            sys.exit(1)

    if not password:
        print("Password cannot be empty. Aborting.")
        sys.exit(1)

    with session_factory() as session:
        existing = session.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()

        if existing:
            print(f"User '{username}' already exists (role={existing.role}). Nothing to do.")
            sys.exit(0)

        user = User(
            username=username,
            hashed_password=hash_password(password),
            role="super_user",
            is_active=True,
        )
        session.add(user)
        session.commit()
        print(f"Created super_user '{username}' successfully.")


if __name__ == "__main__":
    main()
