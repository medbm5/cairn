"""Sentry error monitoring. A no-op when SENTRY_DSN is empty."""

import sentry_sdk

from cairn.config import Settings


def init_sentry(settings: Settings) -> bool:
    """Initialise Sentry if a DSN is configured. Returns whether it was enabled."""
    if not settings.sentry_dsn:
        return False
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        release=settings.release or None,
        traces_sample_rate=0.1,
        send_default_pii=False,
    )
    return True


def tag_request(request_id: str) -> None:
    """Attach the request ID to events from the current request (no-op without Sentry)."""
    sentry_sdk.set_tag("request_id", request_id)
