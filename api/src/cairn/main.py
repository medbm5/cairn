"""App factory: middleware, routers."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cairn.config import get_settings
from cairn.logging import configure_logging
from cairn.middleware import REQUEST_ID_HEADER, RequestIdMiddleware
from cairn.routers import health, profiles


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    app = FastAPI(title="Cairn API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER],
    )
    app.add_middleware(RequestIdMiddleware)
    app.include_router(health.router)
    app.include_router(profiles.router)
    return app


app = create_app()
