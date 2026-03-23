"""FastAPI application entrypoint in backend namespace."""

import logging
from time import perf_counter
from uuid import uuid4

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

import backend.interfaces.api.dependencies as deps
from backend.interfaces.api.routes.auth import router as auth_router
from backend.interfaces.api.routes.checks import router as checks_router
from backend.interfaces.api.routes.customers import router as customers_router
from backend.interfaces.api.routes.dashboard import router as dashboard_router
from backend.interfaces.api.routes.findings import router as findings_router
from backend.interfaces.api.routes.history import router as history_router
from backend.interfaces.api.routes.metrics import router as metrics_router
from backend.interfaces.api.routes.profiles import router as profiles_router
from backend.interfaces.api.routes.sessions import router as sessions_router
from backend.interfaces.api.routes.terminal import router as terminal_router
from backend.config.settings import get_settings


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Build the API application."""
    settings = get_settings()
    _configure_logging(settings.log_level)

    application = FastAPI(
        title="Monitoring Hub API",
        version="0.2.0",
        description="Web-based AWS monitoring platform",
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.middleware("http")
    async def request_logging_middleware(request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        start = perf_counter()

        response = await call_next(request)

        duration_ms = round((perf_counter() - start) * 1000, 2)
        response.headers["x-request-id"] = request_id
        logger.info(
            "request_id=%s %s %s -> %s in %.2fms",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response

    # Auth routes are public — no api_dependencies applied
    application.include_router(auth_router, prefix="/api/v1")

    api_dependencies = [Depends(deps.require_api_key)]
    application.include_router(
        customers_router,
        prefix="/api/v1",
        dependencies=api_dependencies,
    )
    application.include_router(
        checks_router,
        prefix="/api/v1",
        dependencies=api_dependencies,
    )
    application.include_router(
        history_router,
        prefix="/api/v1",
        dependencies=api_dependencies,
    )
    application.include_router(
        findings_router,
        prefix="/api/v1",
        dependencies=api_dependencies,
    )
    application.include_router(
        metrics_router,
        prefix="/api/v1",
        dependencies=api_dependencies,
    )
    application.include_router(
        dashboard_router,
        prefix="/api/v1",
        dependencies=api_dependencies,
    )
    application.include_router(
        profiles_router,
        prefix="/api/v1",
        dependencies=api_dependencies,
    )
    application.include_router(
        sessions_router,
        prefix="/api/v1",
        dependencies=api_dependencies,
    )
    # Terminal WebSocket — auth handled inside the route via ?token= query param
    # because browsers cannot set custom headers on WebSocket connections.
    application.include_router(terminal_router, prefix="/api/v1")

    @application.get("/health")
    def health():
        return {"status": "ok", "version": "0.2.0"}

    @application.get("/health/liveness")
    def liveness():
        return {"status": "ok", "version": "0.2.0"}

    @application.get("/health/readiness")
    def readiness():
        try:
            session = deps._get_session_factory()()
            try:
                session.execute(text("SELECT 1"))
            finally:
                session.close()
        except Exception as exc:
            logger.exception("request_id=health-readiness readiness check failed")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "version": "0.2.0",
                    "checks": {"database": "error"},
                    "detail": str(exc),
                },
            )

        return {
            "status": "ready",
            "version": "0.2.0",
            "checks": {"database": "ok"},
        }

    return application


app = create_app()

__all__ = ["app", "create_app"]
