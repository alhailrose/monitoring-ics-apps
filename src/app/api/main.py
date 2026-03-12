"""FastAPI application entrypoint for monitoring web platform."""

import logging
from time import perf_counter
from uuid import uuid4

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

import src.app.api.dependencies as deps
from src.app.api.routes.customers import router as customers_router
from src.app.api.routes.checks import router as checks_router
from src.app.api.routes.history import router as history_router
from src.app.api.routes.profiles import router as profiles_router
from src.app.api.routes.sessions import router as sessions_router
from src.app.settings import get_settings


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

    # CORS
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

    # Routes
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
        profiles_router,
        prefix="/api/v1",
        dependencies=api_dependencies,
    )
    application.include_router(
        sessions_router,
        prefix="/api/v1",
        dependencies=api_dependencies,
    )

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
