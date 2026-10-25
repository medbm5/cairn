import time
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import httpx
import openai
import pytest
import structlog
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from cairn import observability
from cairn.explain.client import GeneratedExplanation, OpenAIExplainer
from cairn.explain.facts import Topic
from cairn.explain.service import ResponseCache, explain, usable_title
from cairn.models import ObservabilityEvent
from cairn.routers import explain as explain_router
from tests.test_explain import good_output, parsed


@pytest.fixture(autouse=True)
def fresh_recorder() -> Iterator[None]:
    observability.recorder.reset()
    explain_router.response_cache.clear()
    explain_router.rate_limiter.reset()
    yield
    observability.recorder.reset()


def pending(kind: type[observability.Record]) -> list[Any]:
    return [r for r in observability.recorder.pending() if isinstance(r, kind)]


def explainer_returning(output: GeneratedExplanation | None, model: str) -> OpenAIExplainer:
    explainer = OpenAIExplainer("sk-test", model, max_retries=0)
    usage = SimpleNamespace(
        input_tokens=320,
        output_tokens=90,
        output_tokens_details=SimpleNamespace(reasoning_tokens=0),
    )
    explainer._client.responses.parse = MagicMock(  # type: ignore[method-assign]
        return_value=SimpleNamespace(output_parsed=output, usage=usage)
    )
    return explainer


# --- LLM calls ---


def test_a_model_call_records_tokens_latency_and_cost() -> None:
    explainer = explainer_returning(good_output(), "gpt-5-nano")
    assert explainer.generate("prompt", topic="projection") is not None
    call = pending(observability.LlmCall)[-1]
    assert (call.topic, call.model, call.ok) == ("projection", "gpt-5-nano", True)
    assert (call.input_tokens, call.output_tokens) == (320, 90)
    assert call.cost_usd == pytest.approx((320 * 0.05 + 90 * 0.40) / 1_000_000)
    kwargs = explainer._client.responses.parse.call_args.kwargs  # type: ignore[attr-defined]
    assert kwargs["reasoning"] == {"effort": "minimal"}
    assert kwargs["max_output_tokens"] == 400


def test_non_reasoning_models_get_no_reasoning_setting() -> None:
    explainer = explainer_returning(good_output(), "gpt-4o-mini")
    explainer.generate("prompt")
    kwargs = explainer._client.responses.parse.call_args.kwargs  # type: ignore[attr-defined]
    assert "reasoning" not in kwargs


def test_failed_calls_are_recorded() -> None:
    explainer = OpenAIExplainer("sk-test", "gpt-5-nano", max_retries=0)
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    explainer._client.responses.parse = MagicMock(  # type: ignore[method-assign]
        side_effect=openai.APITimeoutError(request=request)
    )
    assert explainer.generate("prompt", topic="allocation") is None
    call = pending(observability.LlmCall)[-1]
    assert (call.ok, call.error, call.cost_usd) == (False, "APITimeoutError", 0.0)


def test_unknown_models_have_no_cost_estimate() -> None:
    assert observability.estimate_cost_usd("some-new-model", 1_000, 1_000) is None


# --- Explanations ---


def test_explanations_record_where_the_text_came_from() -> None:
    explainer = explainer_returning(good_output(), "gpt-5-nano")
    cache = ResponseCache()
    for _ in range(2):  # the second identical request is served from the cache
        explain(
            topic=Topic.PROJECTION,
            facts=parsed(Topic.PROJECTION),
            term=None,
            level="simple",
            language="en",
            explainer=explainer,
            cache=cache,
        )
    explain(
        topic=Topic.PROJECTION,
        facts=parsed(Topic.PROJECTION),
        term=None,
        level="more_detail",
        language="en",
        explainer=None,
        cache=cache,
    )
    records = [(e.source, e.reason) for e in pending(observability.ExplanationRecord)]
    assert records == [("ai", None), ("cache", None), ("fallback", "no_key")]


def test_glossary_terms_never_call_the_model() -> None:
    explainer = explainer_returning(good_output(), "gpt-5-nano")
    result = explain(
        topic=Topic.TERM,
        facts=None,
        term="bond",
        level="simple",
        language="en",
        explainer=explainer,
        cache=ResponseCache(),
    )
    assert result.title == "Bond"
    explainer._client.responses.parse.assert_not_called()  # type: ignore[attr-defined]
    assert pending(observability.ExplanationRecord)[-1].reason == "glossary"


def test_schema_name_is_never_shown_as_a_title() -> None:
    assert usable_title("GeneratedExplanation", "What happened") == "What happened"
    assert usable_title("  ", "What happened") == "What happened"
    assert usable_title("Your March in numbers", "What happened") == "Your March in numbers"


# --- HTTP ---


def test_stats_cover_requests_llm_usage_and_the_log_trail(client: TestClient) -> None:
    client.app.dependency_overrides[explain_router.get_explainer] = lambda: None  # type: ignore[attr-defined]
    client.get("/profiles")
    client.get("/goals/12345")  # a 404, recorded with its route template
    client.post("/explain", json={"topic": "term", "term": "bond"})
    structlog.get_logger("test").warning("something.odd", detail="x" * 500)
    client.get("/observability/stats")  # its own polling is not counted

    stats = client.get("/observability/stats").json()
    api = stats["api"]
    assert api["requests"] == 3
    assert api["status_counts"] == {"2xx": 2, "4xx": 1}
    routes = {(r["method"], r["route"]): r["count"] for r in api["routes"]}
    assert routes[("GET", "/goals/{goal_id}")] == 1
    assert api["recent"][0]["route"] == "/explain"
    assert len(api["recent"][0]["request_id"]) == 32

    llm = stats["llm"]
    assert llm["explanations"] == 1
    assert llm["sources"] == {"fallback": 1}
    assert llm["fallback_reasons"] == {"glossary": 1}
    assert llm["calls"] == 0 and llm["cost_usd"] is None

    # Request log lines are not stored twice; other log lines are, with long values cut short.
    events = [line["event"] for line in stats["logs"]]
    assert "request" not in events
    odd = next(line for line in stats["logs"] if line["event"] == "something.odd")
    assert odd["level"] == "warning" and len(odd["fields"]["detail"]) == 200


# --- Persistence ---


def test_events_survive_a_restart(client: TestClient, session: Session) -> None:
    client.get("/profiles")
    client.get("/observability/stats")  # writes the pending events to the database
    observability.recorder.reset()  # what a restart does to the in-memory buffer
    assert session.scalar(select(func.count(ObservabilityEvent.id))) == 1
    assert client.get("/observability/stats").json()["api"]["requests"] == 1


def test_old_events_are_pruned(session: Session) -> None:
    old = datetime.now(UTC) - timedelta(days=8)
    observability.recorder.add(
        observability.RequestRecord(old, "GET", "/old", "/old", 200, 1.0, "a" * 32)
    )
    observability.recorder.add(
        observability.RequestRecord(datetime.now(UTC), "GET", "/new", "/new", 200, 1.0, "b" * 32)
    )
    observability.flush(session)  # writes both
    observability.recorder.last_prune = datetime.min.replace(tzinfo=UTC)
    observability.flush(session, retention_days=7)  # the hourly prune removes the old one
    routes = list(session.scalars(select(ObservabilityEvent.data)))
    assert [r["route"] for r in routes] == ["/new"]


def test_a_failing_database_never_breaks_the_api() -> None:
    broken = MagicMock(spec=Session)
    broken.commit.side_effect = RuntimeError("database is down")
    observability.recorder.add(
        observability.RequestRecord(datetime.now(UTC), "GET", "/", "/", 200, 1.0, None)
    )
    assert observability.flush(broken) == 0
    broken.rollback.assert_called_once()
    # The failure itself is logged, and kept for the next flush.
    assert [r.event for r in pending(observability.LogLine)] == ["observability.flush_failed"]


def test_the_background_writer_saves_events(session_factory: sessionmaker[Session]) -> None:
    flusher = observability.Flusher(session_factory, interval=0.05, retention_days=7)
    flusher.start()
    try:
        observability.record_explanation("projection", "ai")
        with session_factory() as session:
            for _ in range(100):
                if session.scalar(select(func.count(ObservabilityEvent.id))):
                    break
                time.sleep(0.02)
            kinds = list(session.scalars(select(ObservabilityEvent.kind)))
    finally:
        flusher.stop()
    assert "explanation" in kinds
