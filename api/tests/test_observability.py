from collections.abc import Iterator
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import openai
import pytest
from fastapi.testclient import TestClient

from cairn import observability
from cairn.explain.client import GeneratedExplanation, OpenAIExplainer
from cairn.explain.facts import Topic
from cairn.explain.service import ResponseCache, explain, usable_title
from cairn.routers import explain as explain_router
from tests.test_explain import good_output, parsed


@pytest.fixture(autouse=True)
def fresh_recorder() -> Iterator[None]:
    observability.recorder.reset()
    explain_router.response_cache.clear()
    explain_router.rate_limiter.reset()
    yield
    observability.recorder.reset()


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
    call = observability.recorder.llm_calls[-1]
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
    call = observability.recorder.llm_calls[-1]
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
    records = [(e.source, e.reason) for e in observability.recorder.explanations]
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
    assert observability.recorder.explanations[-1].reason == "glossary"


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

    events = [line["event"] for line in stats["logs"]]
    assert "request" in events
    request_line = next(line for line in stats["logs"] if line["event"] == "request")
    assert request_line["request_id"] and request_line["fields"]["status"] in (200, 404)
