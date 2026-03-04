"""Dependency providers for API routes."""

from functools import lru_cache

from src.app.settings import get_settings
from src.db.repositories.customer_repository import CustomerRepository
from src.db.repositories.check_repository import CheckRepository
from src.db.session import build_session_factory
from src.app.services.customer_service import CustomerService
from src.app.services.check_executor import CheckExecutor
from src.app.services.session_health import SessionHealthService


@lru_cache(maxsize=1)
def _get_session_factory():
    return build_session_factory(get_settings().database_url)


def _get_session():
    return _get_session_factory()()


def get_customer_service():
    session = _get_session()
    try:
        repo = CustomerRepository(session)
        yield CustomerService(repo)
    finally:
        session.close()


def get_check_executor():
    session = _get_session()
    settings = get_settings()
    try:
        customer_repo = CustomerRepository(session)
        check_repo = CheckRepository(session)
        yield CheckExecutor(
            check_repo=check_repo,
            customer_repo=customer_repo,
            region=settings.default_region,
            max_workers=settings.max_workers,
        )
    finally:
        session.close()


def get_check_repository():
    session = _get_session()
    try:
        yield CheckRepository(session)
    finally:
        session.close()


def get_session_health_service():
    session = _get_session()
    try:
        repo = CustomerRepository(session)
        yield SessionHealthService(customer_repo=repo)
    finally:
        session.close()
