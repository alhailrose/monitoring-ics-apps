"""Dependency providers for API routes."""

import logging
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer

from backend.config.settings import get_settings
from backend.infra.database.repositories.customer_repository import CustomerRepository
from backend.infra.database.repositories.check_repository import CheckRepository
from backend.infra.database.repositories.user_repository import UserRepository
from backend.infra.database.repositories.invite_repository import InviteRepository
from backend.infra.database.session import build_session_factory
from backend.domain.services.customer_service import CustomerService
from backend.domain.services.check_executor import CheckExecutor
from backend.domain.services.session_health import SessionHealthService
from backend.domain.services.auth_service import (
    AuthService,
    InvalidTokenError,
    TokenPayload,
)
from backend.domain.services.invite_service import InviteService
from backend.infra.cloud.aws.clients import user_aws_config_path

logger = logging.getLogger(__name__)

_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


@lru_cache(maxsize=1)
def _get_session_factory():
    return build_session_factory(get_settings().database_url)


def _get_session():
    return _get_session_factory()()


def _resolve_request_aws_config_file(request: Request) -> str | None:
    current_user = getattr(request.state, "auth_user", None)
    username = getattr(current_user, "username", None)
    if not username or username in {"anonymous", "api-key"}:
        return None
    return user_aws_config_path(username)


def get_customer_service(request: Request):
    session = _get_session()
    aws_config_file = _resolve_request_aws_config_file(request)
    try:
        repo = CustomerRepository(session)
        yield CustomerService(repo, aws_config_file=aws_config_file)
    finally:
        session.close()


def get_check_executor(request: Request):
    session = _get_session()
    settings = get_settings()
    aws_config_file = _resolve_request_aws_config_file(request)
    try:
        customer_repo = CustomerRepository(session)
        check_repo = CheckRepository(session)
        yield CheckExecutor(
            check_repo=check_repo,
            customer_repo=customer_repo,
            region=settings.default_region,
            max_workers=settings.max_workers,
            timeout=settings.execution_timeout,
            aws_config_file=aws_config_file,
        )
    finally:
        session.close()


def get_check_repository():
    session = _get_session()
    try:
        yield CheckRepository(session)
    finally:
        session.close()


def get_session_health_service(request: Request):
    session = _get_session()
    aws_config_file = _resolve_request_aws_config_file(request)
    try:
        repo = CustomerRepository(session)
        yield SessionHealthService(customer_repo=repo, aws_config_file=aws_config_file)
    finally:
        session.close()


def get_auth_service():
    session = _get_session()
    settings = get_settings()
    try:
        repo = UserRepository(session)
        yield AuthService(
            user_repo=repo,
            jwt_secret=settings.jwt_secret,
            jwt_expire_hours=settings.jwt_expire_hours,
        )
    finally:
        session.close()


def require_auth(
    token: Annotated[str | None, Depends(_oauth2_scheme)],
    request: Request,
) -> TokenPayload:
    """Validate JWT Bearer token and return the decoded payload.

    During the transition period, also accepts a valid API key and returns a
    synthetic super_user payload so existing integrations continue to work.
    Logs a deprecation warning when an API key is used.
    """
    settings = get_settings()

    # -- Auth disabled bypass (matches require_api_key behaviour) --
    if not settings.api_auth_enabled:
        payload = TokenPayload(
            user_id="anonymous", username="anonymous", role="super_user"
        )
        request.state.auth_user = payload
        return payload

    # -- JWT path --
    if token:
        # First check if it's a valid API key (before trying JWT decode)
        if settings.api_auth_enabled and token in settings.api_keys:
            logger.warning(
                "API key auth is deprecated — migrate to JWT via POST /api/v1/auth/login"
            )
            payload = TokenPayload(
                user_id="api-key", username="api-key", role="super_user"
            )
            request.state.auth_user = payload
            return payload

        session = _get_session_factory()()
        try:
            repo = UserRepository(session)
            auth_svc = AuthService(
                user_repo=repo,
                jwt_secret=settings.jwt_secret,
                jwt_expire_hours=settings.jwt_expire_hours,
            )
            try:
                payload = auth_svc.decode_token(token)
                request.state.auth_user = payload
                return payload
            except InvalidTokenError as exc:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=str(exc),
                    headers={"WWW-Authenticate": "Bearer"},
                )
        finally:
            session.close()

    # -- Legacy API key fallback (X-API-Key header) --
    if settings.api_auth_enabled:
        provided_key = request.headers.get(settings.api_key_header)
        if provided_key and provided_key in settings.api_keys:
            logger.warning(
                "API key auth is deprecated — migrate to JWT via POST /api/v1/auth/login"
            )
            payload = TokenPayload(
                user_id="api-key", username="api-key", role="super_user"
            )
            request.state.auth_user = payload
            return payload

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_invite_service():
    session = _get_session()
    settings = get_settings()
    try:
        user_repo = UserRepository(session)
        invite_repo = InviteRepository(session)
        yield InviteService(
            invite_repo=invite_repo,
            user_repo=user_repo,
            smtp_host=settings.smtp_host,
            smtp_port=settings.smtp_port,
            smtp_user=settings.smtp_user,
            smtp_password=settings.smtp_password,
            smtp_from=settings.smtp_from,
            app_base_url=settings.app_base_url,
            invite_expire_hours=settings.invite_expire_hours,
        )
    finally:
        session.close()


def require_role(required_role: str):
    """Return a FastAPI dependency that enforces a minimum role.

    Usage:
        @router.post("/", dependencies=[Depends(require_role("super_user"))])
    """

    def _check(current_user: Annotated[TokenPayload, Depends(require_auth)]):
        role_hierarchy = {"super_user": 2, "user": 1}
        user_level = role_hierarchy.get(current_user.role, 0)
        required_level = role_hierarchy.get(required_role, 99)
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required",
            )

    return _check


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
