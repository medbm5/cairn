"""In-process observability for the demo: recent API requests, LLM calls and log lines.

Everything lives in bounded in-memory buffers, so it covers the time since the API last started
(free hosting restarts it often) and costs nothing to run. Production would ship the same events
to a metrics and log backend instead; Sentry already receives errors.
"""

import threading
from collections import Counter, deque
from collections.abc import Iterable, Mapping, MutableMapping
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

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
    request_id: str


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
    at: str
    level: str
    event: str
    logger: str | None
    request_id: str | None
    fields: dict[str, Any]


@dataclass
class Recorder:
    max_requests: int = 2_000
    max_llm_calls: int = 500
    max_explanations: int = 1_000
    max_logs: int = 300
    started_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        self._lock = threading.Lock()
        self.requests: deque[RequestRecord] = deque(maxlen=self.max_requests)
        self.llm_calls: deque[LlmCall] = deque(maxlen=self.max_llm_calls)
        self.explanations: deque[ExplanationRecord] = deque(maxlen=self.max_explanations)
        self.logs: deque[LogLine] = deque(maxlen=self.max_logs)

    def add(self, record: RequestRecord | LlmCall | ExplanationRecord | LogLine) -> None:
        with self._lock:
            match record:
                case RequestRecord():
                    self.requests.append(record)
                case LlmCall():
                    self.llm_calls.append(record)
                case ExplanationRecord():
                    self.explanations.append(record)
                case LogLine():
                    self.logs.append(record)

    def snapshot(
        self,
    ) -> tuple[list[RequestRecord], list[LlmCall], list[ExplanationRecord], list[LogLine]]:
        with self._lock:
            return (
                list(self.requests),
                list(self.llm_calls),
                list(self.explanations),
                list(self.logs),
            )

    def reset(self) -> None:
        with self._lock:
            self.requests.clear()
            self.llm_calls.clear()
            self.explanations.clear()
            self.logs.clear()
            self.started_at = _now()


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
    """structlog processor: keep a copy of every log line for the log trail."""
    recorder.add(
        LogLine(
            at=str(event_dict.get("timestamp", _now().isoformat())),
            level=str(event_dict.get("level", "info")),
            event=str(event_dict.get("event", "")),
            logger=event_dict.get("logger"),
            request_id=event_dict.get("request_id"),
            fields={k: _short(v) for k, v in event_dict.items() if k not in _LOG_SKIP},
        )
    )
    return event_dict


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


def _jsonable(record: object) -> dict[str, Any]:
    data = asdict(record)  # type: ignore[call-overload]
    return {k: v.isoformat() if isinstance(v, datetime) else v for k, v in data.items()}


def stats(model: str, ai_enabled: bool, recent: int = 50) -> dict[str, Any]:
    """Everything the observability page shows, computed from the buffers."""
    requests, calls, explanations, logs = recorder.snapshot()
    durations = [r.duration_ms for r in requests]
    statuses: Mapping[str, int] = Counter(f"{r.status // 100}xx" for r in requests)
    sources = Counter(e.source for e in explanations)
    reasons = Counter(e.reason for e in explanations if e.reason)
    ok_calls = [c for c in calls if c.ok]
    costs = [c.cost_usd for c in calls if c.cost_usd is not None]
    return {
        "since": recorder.started_at.isoformat(),
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
