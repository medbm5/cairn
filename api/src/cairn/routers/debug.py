"""Local-only routes for checking the monitoring setup. Not mounted outside ENVIRONMENT=local."""

from fastapi import APIRouter

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/sentry")
def trigger_error() -> None:
    raise RuntimeError("Test error from /debug/sentry, to check that Sentry receives events.")
