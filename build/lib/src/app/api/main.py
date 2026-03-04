"""FastAPI application entrypoint for monitoring web platform."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.api.routes.customers import router as customers_router
from src.app.api.routes.checks import router as checks_router
from src.app.api.routes.history import router as history_router
from src.app.api.routes.profiles import router as profiles_router
from src.app.api.routes.sessions import router as sessions_router
from src.app.settings import get_settings


def create_app() -> FastAPI:
    """Build the API application."""
    settings = get_settings()

    application = FastAPI(
        title="Monitoring Hub API",
        version="0.2.0",
        description="Web-based AWS monitoring platform",
    )

    # CORS
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    application.include_router(customers_router, prefix="/api/v1")
    application.include_router(checks_router, prefix="/api/v1")
    application.include_router(history_router, prefix="/api/v1")
    application.include_router(profiles_router, prefix="/api/v1")
    application.include_router(sessions_router, prefix="/api/v1")

    @application.get("/health")
    def health():
        return {"status": "ok", "version": "0.2.0"}

    return application


app = create_app()
