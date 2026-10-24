"""App factory: middleware, routers."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cairn.config import get_settings
from cairn.logging import configure_logging
from cairn.middleware import REQUEST_ID_HEADER, RequestIdMiddleware
from cairn.monitoring import init_sentry
from cairn.routers import (
    debug,
    explain,
    glide_path,
    goals,
    health,
    ledger,
    profiles,
    simulations,
    stress,
    support,
)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    init_sentry(settings)
    app = FastAPI(title="Cairn API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER],
    )
    app.add_middleware(RequestIdMiddleware)
    app.include_router(health.router)
    app.include_router(profiles.router)
    app.include_router(simulations.router)
    app.include_router(glide_path.router)
    app.include_router(goals.router)
    app.include_router(ledger.router)
    app.include_router(stress.router)
    app.include_router(explain.router)
    app.include_router(support.router)
    if settings.environment == "local":
        app.include_router(debug.router)
    return app


app = create_app()
