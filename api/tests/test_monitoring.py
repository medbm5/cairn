from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from cairn.config import Settings, get_settings
from cairn.main import create_app
from cairn.monitoring import init_sentry


@pytest.fixture
def environment(monkeypatch: pytest.MonkeyPatch) -> Iterator[pytest.MonkeyPatch]:
    get_settings.cache_clear()
    yield monkeypatch
    get_settings.cache_clear()


def test_sentry_is_a_no_op_without_dsn() -> None:
    assert init_sentry(Settings(sentry_dsn="")) is False


def test_release_reads_render_commit(environment: pytest.MonkeyPatch) -> None:
    environment.setenv("RENDER_GIT_COMMIT", "abc123")
    assert get_settings().release == "abc123"


def test_debug_route_exists_only_locally(environment: pytest.MonkeyPatch) -> None:
    environment.setenv("ENVIRONMENT", "local")
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        assert client.get("/debug/sentry").status_code == 500

    get_settings.cache_clear()
    environment.setenv("ENVIRONMENT", "production")
    with TestClient(create_app()) as client:
        assert client.get("/debug/sentry").status_code == 404


@pytest.mark.parametrize(
    "url",
    ["postgres://u:p@host:5432/cairn", "postgresql://u:p@host:5432/cairn"],
)
def test_hosted_database_urls_use_psycopg(url: str) -> None:
    assert Settings(database_url=url).database_url == "postgresql+psycopg://u:p@host:5432/cairn"


def test_cors_allows_only_configured_origins(environment: pytest.MonkeyPatch) -> None:
    environment.setenv("CORS_ORIGINS", "https://cairn.vercel.app,http://localhost:5173")
    with TestClient(create_app()) as client:
        allowed = client.options(
            "/health",
            headers={"Origin": "https://cairn.vercel.app", "Access-Control-Request-Method": "GET"},
        )
        denied = client.options(
            "/health",
            headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
        )
    assert allowed.headers["access-control-allow-origin"] == "https://cairn.vercel.app"
    assert "access-control-allow-origin" not in denied.headers
