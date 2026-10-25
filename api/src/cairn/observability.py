"""Observability for the demo: API requests, AI calls, explanation outcomes and log lines.

Events are first kept in a small in-memory buffer, so recording never slows a request down. A
background thread writes them to the `observability_events` table every few seconds, and the stats
endpoint writes whatever is still pending before it reads. The page then shows the last 24 hours
from the database, so a restart loses at most a few seconds. Events older than the retention
period are pruned. Sentry still receives errors.
"""

import threading
from collections import Counter, deque
from collections.abc import Callable, Iterable, Mapping, MutableMapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from cairn.models import ObservabilityEvent

# Estimated prices in US dollars per million tokens (input, output). Check OpenAI's pricing page:
# these change, and an unknown model simply shows no cost.
MODEL_PRICES_USD_PER_M: dict[str, tuple[float, float]] = {
    "gpt-5-nano": (0.05, 0.40),
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-5-mini": (0.25, 2.00),
}

# Log fields that are noise in the trail, already shown elsewhere, or too long to keep.
_LOG_SKIP = {"event", "level", "timestamp", "request_id", "logger"}
_LOG_VALUE_LIMIT = 200
# Each request already has its own record; storing its log line too would double the writes.
_LOG_EVENTS_NOT_KEPT = {"request"}

WINDOW = timedelta(hours=24)
MAX_PENDING = 5_000  # if the database is down, the oldest unsaved events are dropped
PRUNE_EVERY = timedelta(hours=1)


def _now() -> datetime:
    return datetime.now(UTC)


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float | None:
    prices = MODEL_PRICES_USD_PER_M.get(model)
    if prices is None:
        return None
    return (input_tokens * prices[0] + output_tokens * prices[1]) / 1_000_000


@dataclass(frozen=True)
class RequestRecord:
    at: datetime
    method: str
    route: str  # the route template, e.g. /goals/{goal_id}
    path: str
    status: int
    duration_ms: float
    request_id: str | None


@dataclass(frozen=True)
class LlmCall:
    at: datetime
    topic: str
    model: str
    ok: bool
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    latency_ms: float
    cost_usd: float | None
    error: str | None
    request_id: str | None


@dataclass(frozen=True)
class ExplanationRecord:
    """How one explanation was produced: ai, or fallback with a reason, or served from cache."""

    at: datetime
    topic: str
    source: str  # ai | cache | fallback
    reason: str | None  # no_key, glossary, model_error, guard_rejected
    request_id: str | None


@dataclass(frozen=True)
class LogLine:
    at: datetime
    level: str
    event: str
    logger: str | None
    request_id: str | None
    fields: dict[str, Any]


Record = RequestRecord | LlmCall | ExplanationRecord | LogLine

KINDS: dict[str, type[Record]] = {
    "request": RequestRecord,
    "llm_call": LlmCall,
    "explanation": ExplanationRecord,
    "log": LogLine,
}
KIND_OF: dict[type[Record], str] = {cls: kind for kind, cls in KINDS.items()}


def to_row(record: Record) -> ObservabilityEvent:
    data = {k: v for k, v in asdict(record).items() if k not in ("at", "request_id")}
    return ObservabilityEvent(
        at=record.at, kind=KIND_OF[type(record)], request_id=record.request_id, data=data
    )


def from_row(row: ObservabilityEvent) -> Record:
    at = row.at if row.at.tzinfo else row.at.replace(tzinfo=UTC)  # SQLite drops the zone
    return KINDS[row.kind](at=at, request_id=row.request_id, **row.data)


class Recorder:
    """Events waiting to be written to the database."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pending: deque[Record] = deque(maxlen=MAX_PENDING)
        self.last_prune = datetime.min.replace(tzinfo=UTC)

    def add(self, record: Record) -> None:
        with self._lock:
            self._pending.append(record)

    def pending(self) -> list[Record]:
        with self._lock:
            return list(self._pending)

    def drain(self) -> list[Record]:
        with self._lock:
            records = list(self._pending)
            self._pending.clear()
            return records

    def reset(self) -> None:
        with self._lock:
            self._pending.clear()
            self.last_prune = datetime.min.replace(tzinfo=UTC)


recorder = Recorder()


# --- Recording helpers ---


def current_request_id() -> str | None:
    value = structlog.contextvars.get_contextvars().get("request_id")
    return str(value) if value else None


def record_llm_call(
    *,
    topic: str,
    model: str,
    ok: bool,
    input_tokens: int = 0,
    output_tokens: int = 0,
    reasoning_tokens: int = 0,
    latency_ms: float,
    error: str | None = None,
) -> None:
    recorder.add(
        LlmCall(
            at=_now(),
            topic=topic,
            model=model,
            ok=ok,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=reasoning_tokens,
            latency_ms=round(latency_ms, 1),
            cost_usd=estimate_cost_usd(model, input_tokens, output_tokens),
            error=error,
            request_id=current_request_id(),
        )
    )


def record_explanation(topic: str, source: str, reason: str | None = None) -> None:
    recorder.add(
        ExplanationRecord(
            at=_now(), topic=topic, source=source, reason=reason, request_id=current_request_id()
        )
    )


def _short(value: object) -> object:
    if isinstance(value, str | int | float | bool) or value is None:
        return value[:_LOG_VALUE_LIMIT] if isinstance(value, str) else value
    return str(value)[:_LOG_VALUE_LIMIT]


def capture_log(
    _logger: object, _method: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """structlog processor: keep a copy of log lines for the log trail."""
    event = str(event_dict.get("event", ""))
    if event not in _LOG_EVENTS_NOT_KEPT:
        recorder.add(
            LogLine(
                at=_now(),
                level=str(event_dict.get("level", "info")),
                event=event,
                logger=event_dict.get("logger"),
                request_id=event_dict.get("request_id"),
                fields={k: _short(v) for k, v in event_dict.items() if k not in _LOG_SKIP},
            )
        )
    return event_dict


# --- Writing to the database ---


def flush(session: Session, retention_days: int = 7) -> int:
    """Write pending events, and prune old ones about once an hour. Returns how many were written.

    On a database error the events are dropped rather than retried forever: observability must
    never take the API down with it.
    """
    records = recorder.drain()
    now = _now()
    prune = now - recorder.last_prune >= PRUNE_EVERY
    if not records and not prune:
        return 0
    try:
        session.add_all([to_row(r) for r in records])
        if prune:
            cutoff = now - timedelta(days=retention_days)
            session.execute(delete(ObservabilityEvent).where(ObservabilityEvent.at < cutoff))
            recorder.last_prune = now
        session.commit()
    except Exception:
        session.rollback()
        structlog.get_logger("cairn.observability").warning(
            "observability.flush_failed", dropped=len(records)
        )
        return 0
    return len(records)


class Flusher:
    """A daemon thread that writes pending events every `interval` seconds."""

    def __init__(
        self, session_factory: Callable[[], Session], interval: float, retention_days: int
    ) -> None:
        self._session_factory = session_factory
        self._interval = interval
        self._retention_days = retention_days
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="observability-flush", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=self._interval + 5)
        self._flush()  # whatever arrived during shutdown

    def _flush(self) -> None:
        with self._session_factory() as session:
            flush(session, self._retention_days)

    def _run(self) -> None:
        while not self._stop.wait(self._interval):
            self._flush()


def load(session: Session, since: datetime) -> list[Record]:
    rows = session.scalars(
        select(ObservabilityEvent)
        .where(ObservabilityEvent.at >= since)
        .order_by(ObservabilityEvent.at, ObservabilityEvent.id)
    )
    return [from_row(row) for row in rows]


# --- Summaries ---


def percentile(values: list[float], share: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(share * (len(ordered) - 1))))
    return ordered[index]


def _route_rows(requests: Iterable[RequestRecord]) -> list[dict[str, Any]]:
    by_route: dict[tuple[str, str], list[RequestRecord]] = {}
    for r in requests:
        by_route.setdefault((r.method, r.route), []).append(r)
    rows = []
    for (method, route), records in by_route.items():
        durations = [r.duration_ms for r in records]
        rows.append(
            {
                "method": method,
                "route": route,
                "count": len(records),
                "errors": sum(r.status >= 500 for r in records),
                "p50_ms": percentile(durations, 0.5),
                "p95_ms": percentile(durations, 0.95),
            }
        )
    return sorted(rows, key=lambda row: -row["count"])


def _topic_rows(
    calls: Iterable[LlmCall], explanations: Iterable[ExplanationRecord]
) -> list[dict[str, Any]]:
    topics: dict[str, dict[str, Any]] = {}

    def row(topic: str) -> dict[str, Any]:
        return topics.setdefault(
            topic,
            {
                "topic": topic,
                "explanations": 0,
                "ai": 0,
                "cache": 0,
                "fallback": 0,
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
            },
        )

    for e in explanations:
        r = row(e.topic)
        r["explanations"] += 1
        r[e.source] += 1
    for c in calls:
        r = row(c.topic)
        r["calls"] += 1
        r["input_tokens"] += c.input_tokens
        r["output_tokens"] += c.output_tokens
        r["cost_usd"] += c.cost_usd or 0.0
    return sorted(topics.values(), key=lambda r: -r["explanations"])


def _jsonable(record: Record) -> dict[str, Any]:
    data = asdict(record)
    return {k: v.isoformat() if isinstance(v, datetime) else v for k, v in data.items()}


def stats(
    session: Session, model: str, ai_enabled: bool, recent: int = 50, retention_days: int = 7
) -> dict[str, Any]:
    """Everything the observability page shows, for the last 24 hours, read from the database."""
    flush(session, retention_days)
    since = _now() - WINDOW
    records = load(session, since)
    requests = [r for r in records if isinstance(r, RequestRecord)]
    calls = [r for r in records if isinstance(r, LlmCall)]
    explanations = [r for r in records if isinstance(r, ExplanationRecord)]
    logs = [r for r in records if isinstance(r, LogLine)]

    durations = [r.duration_ms for r in requests]
    statuses: Mapping[str, int] = Counter(f"{r.status // 100}xx" for r in requests)
    sources = Counter(e.source for e in explanations)
    reasons = Counter(e.reason for e in explanations if e.reason)
    ok_calls = [c for c in calls if c.ok]
    costs = [c.cost_usd for c in calls if c.cost_usd is not None]
    return {
        "since": since.isoformat(),
        "api": {
            "requests": len(requests),
            "status_counts": dict(statuses),
            "error_rate": (statuses.get("5xx", 0) / len(requests)) if requests else 0.0,
            "p50_ms": percentile(durations, 0.5),
            "p95_ms": percentile(durations, 0.95),
            "routes": _route_rows(requests),
            "recent": [_jsonable(r) for r in reversed(requests[-recent:])],
        },
        "llm": {
            "model": model,
            "enabled": ai_enabled,
            "explanations": len(explanations),
            "sources": dict(sources),
            "fallback_reasons": dict(reasons),
            "calls": len(calls),
            "failed_calls": len(calls) - len(ok_calls),
            "input_tokens": sum(c.input_tokens for c in calls),
            "output_tokens": sum(c.output_tokens for c in calls),
            "reasoning_tokens": sum(c.reasoning_tokens for c in calls),
            "cost_usd": sum(costs) if costs else None,
            "avg_latency_ms": (sum(c.latency_ms for c in calls) / len(calls)) if calls else 0.0,
            "topics": _topic_rows(calls, explanations),
            "recent": [_jsonable(c) for c in reversed(calls[-recent:])],
        },
        "logs": [_jsonable(line) for line in reversed(logs[-recent * 2 :])],
    }
