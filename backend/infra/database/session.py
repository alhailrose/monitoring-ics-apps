"""Database session helpers."""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from backend.infra.database.models import Base


def build_engine(database_url: str):
    """Create SQLAlchemy engine with appropriate settings."""
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    engine = create_engine(
        database_url,
        future=True,
        pool_pre_ping=True,
        connect_args=connect_args,
    )

    if database_url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def build_session_factory(database_url: str) -> sessionmaker[Session]:
    """Build a session factory. Schema is managed by Alembic migrations."""
    engine = build_engine(database_url)
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
