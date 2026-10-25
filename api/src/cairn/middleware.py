"""Request-ID middleware: reuses an incoming X-Request-ID or creates one, and returns it."""

import time
import uuid
from datetime import UTC, datetime

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from cairn.logging import get_logger
from cairn.monitoring import tag_request
from cairn.observability import RequestRecord, recorder

REQUEST_ID_HEADER = "X-Request-ID"
log = get_logger("cairn.http")


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        request.state.request_id = request_id
        tag_request(request_id)
        started = time.perf_counter()
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        duration_ms = round((time.perf_counter() - started) * 1000, 1)
        log.info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )
        # The observability page polls itself; its own requests would only add noise.
        if not request.url.path.startswith("/observability"):
            route = request.scope.get("route")
            recorder.add(
                RequestRecord(
                    at=datetime.now(UTC),
                    method=request.method,
                    route=getattr(route, "path", request.url.path),
                    path=request.url.path,
                    status=response.status_code,
                    duration_ms=duration_ms,
                    request_id=request_id,
                )
            )
        return response
