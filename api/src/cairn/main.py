"""App factory: middleware, routers, and the background writer for observability events."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cairn.config import get_settings
from cairn.db import get_sessionmaker
from cairn.logging import configure_logging
from cairn.middleware import REQUEST_ID_HEADER, RequestIdMiddleware
from cairn.monitoring import init_sentry
from cairn.observability import Flusher
from cairn.routers import (
    debug,
    explain,
    glide_path,
    goals,
    health,
    ledger,
    observability,
    profiles,
    simulations,
    stress,
    support,
)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    init_sentry(settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        flusher = None
        if settings.observability_flush_seconds > 0:
            flusher = Flusher(
                get_sessionmaker(),
                settings.observability_flush_seconds,
                settings.observability_retention_days,
            )
            flusher.start()
        yield
        if flusher is not None:
            flusher.stop()

    app = FastAPI(title="Cairn API", version="0.1.0", lifespan=lifespan)
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
    app.include_router(observability.router)
    if settings.environment == "local":
        app.include_router(debug.router)
    return app


app = create_app()
