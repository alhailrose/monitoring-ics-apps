"""Dependency providers for API routes."""

from functools import lru_cache

from fastapi import HTTPException, Request, status

from backend.config.settings import get_settings
from backend.infra.database.repositories.customer_repository import CustomerRepository
from backend.infra.database.repositories.check_repository import CheckRepository
from backend.infra.database.session import build_session_factory
from backend.domain.services.customer_service import CustomerService
from backend.domain.services.check_executor import CheckExecutor
from backend.domain.services.session_health import SessionHealthService


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
            timeout=settings.execution_timeout,
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


def require_api_key(request: Request):
    """Protect API routes with optional API key auth.

    Auth is enabled only when `API_AUTH_ENABLED=true`.
    Accepted credentials:
    - Header named by `API_KEY_HEADER` (default: X-API-Key)
    - Authorization: Bearer <token>
    """
    settings = get_settings()
    if not settings.api_auth_enabled:
        return

    provided_key = request.headers.get(settings.api_key_header)
    if not provided_key:
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            provided_key = auth_header.split(" ", 1)[1].strip()

    if provided_key in settings.api_keys:
        return

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key",
    )
