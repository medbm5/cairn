from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from cairn.domain.profiles import RiskProfile
from cairn.explain.client import GeneratedExplanation, OpenAIExplainer
from cairn.explain.facts import FACT_MODELS, FactsModel, ProjectionFacts, Topic
from cairn.explain.fallbacks import fallback
from cairn.explain.glossary import GLOSSARY
from cairn.explain.guard import numbers_in, unknown_numbers
from cairn.explain.service import WORD_LIMITS, ResponseCache, explain
from cairn.routers import explain as explain_router

SAMPLE_FACTS: dict[Topic, dict[str, Any]] = {
    Topic.PROJECTION: {
        "profile": "balanced",
        "target_cents": 1_200_000_00,
        "horizon_months": 240,
        "monthly_contribution_cents": 300_00,
        "p10_cents": 8_500_000,
        "p50_cents": 13_250_000,
        "p90_cents": 21_000_000,
        "success_probability": 0.62,
    },
    Topic.ALLOCATION: {
        "profile": "dynamic",
        "weights": {
            "global_equity": 0.6,
            "emerging_equity": 0.15,
            "euro_gov_bonds": 0.2,
            "money_market": 0.05,
        },
    },
    Topic.GLIDE_PATH: {
        "profile": "bold",
        "years_remaining": 6,
        "equity_share_now": 0.61,
        "equity_share_at_goal": 0.1,
    },
    Topic.REBALANCE: {"largest_drift": 0.072, "threshold": 0.05, "moved_cents": 1_234_56},
    Topic.STRESS_TEST: {
        "scenario": "gfc_2008",
        "start_cents": 2_000_000,
        "max_drawdown": 0.31,
        "max_drawdown_rebalanced": 0.29,
        "months_to_recover": 38,
    },
    Topic.LEDGER_ENTRY: {
        "kind": "deposit",
        "amount_cents": 50_000,
        "accounts": ["external_bank", "holding:global_equity"],
    },
}


def parsed(topic: Topic) -> FactsModel:
    return FACT_MODELS[topic].model_validate(SAMPLE_FACTS[topic])


def fake_explainer(*outputs: GeneratedExplanation | None) -> MagicMock:
    explainer = MagicMock(spec=OpenAIExplainer)
    explainer.generate.side_effect = list(outputs)
    return explainer


# --- Glossary ---


def test_glossary_has_about_25_terms_in_both_languages() -> None:
    assert 22 <= len(GLOSSARY) <= 30
    for key, entry in GLOSSARY.items():
        for field in (entry.term, entry.definition, entry.analogy):
            assert field["en"] and field["fr"], key


def test_glossary_contains_no_digits() -> None:
    for key, entry in GLOSSARY.items():
        for field in (entry.term, entry.definition, entry.analogy):
            for text in field.values():
                assert not numbers_in(text), (key, text)


# --- Fallbacks ---


@pytest.mark.parametrize("topic", [t for t in Topic if t != Topic.TERM])
@pytest.mark.parametrize("level", ["simple", "more_detail"])
@pytest.mark.parametrize("language", ["en", "fr"])
def test_every_topic_has_a_working_fallback(topic: Topic, level: str, language: str) -> None:
    facts = parsed(topic)
    text = fallback(topic, facts, None, level, language)  # type: ignore[arg-type]
    assert text.title and text.body and text.analogy
    assert len(text.body.split()) <= WORD_LIMITS[level]
    assert all(term in GLOSSARY for term in text.terms_used)
    # Templates obey the same number guard as the model.
    assert unknown_numbers(f"{text.title} {text.body}", facts) == []


def test_rebalance_fallback_without_drift() -> None:
    facts = FACT_MODELS[Topic.REBALANCE].model_validate({"threshold": 0.05, "moved_cents": 5_000})
    text = fallback(Topic.REBALANCE, facts, None, "simple", "en")
    assert "by more than the 5%" in text.body
    assert unknown_numbers(text.body, facts) == []


def test_term_fallback_uses_glossary() -> None:
    text = fallback(Topic.TERM, None, "volatility", "simple", "fr")
    assert text.title == "Volatilité"
    assert text.terms_used == ["volatility"]


def test_stress_fallback_without_recovery() -> None:
    facts = FACT_MODELS[Topic.STRESS_TEST].model_validate(
        SAMPLE_FACTS[Topic.STRESS_TEST] | {"months_to_recover": None}
    )
    text = fallback(Topic.STRESS_TEST, facts, None, "simple", "en")
    assert "had not fully recovered" in text.body


# --- Guard ---


def test_guard_accepts_reformatted_figures() -> None:
    facts = parsed(Topic.PROJECTION)
    text = (
        "In the middle scenario you could reach €132,500 (about 132 500 €), against a target "
        "of 1.2 million or 1 200 000 €, over 20 years. There is a 62% chance, so 38% of "
        "futures fall short; the P10 case is near 85k."
    )
    assert unknown_numbers(text, facts) == []


def test_guard_rejects_unknown_figure() -> None:
    facts = parsed(Topic.PROJECTION)
    assert unknown_numbers("You will earn 7% a year and reach €150,000.", facts) == [7.0, 150000.0]


# --- Service ---


def good_output() -> GeneratedExplanation:
    return GeneratedExplanation(
        title="Where you could land",
        body="In the middle scenario you would have €132,500. Your chance is 62%.",
        analogy="Like a weather forecast.",
        terms_used=["median", "success_probability", "not_a_term"],
    )


def test_ai_output_is_used_when_it_passes_the_guard() -> None:
    explainer = fake_explainer(good_output())
    result = explain(
        topic=Topic.PROJECTION,
        facts=parsed(Topic.PROJECTION),
        term=None,
        level="simple",
        language="en",
        explainer=explainer,
        cache=ResponseCache(),
    )
    assert result.source == "ai"
    assert result.terms_used == ["median", "success_probability"]
    prompt = explainer.generate.call_args.args[0]
    assert "13250000" in prompt and "WORD LIMIT FOR BODY: 60" in prompt


def test_ai_output_with_unknown_number_falls_back() -> None:
    bad = good_output().model_copy(update={"body": "You will surely get 8% a year."})
    result = explain(
        topic=Topic.PROJECTION,
        facts=parsed(Topic.PROJECTION),
        term=None,
        level="simple",
        language="en",
        explainer=fake_explainer(bad),
        cache=ResponseCache(),
    )
    assert result.source == "fallback"
    assert "8%" not in result.body


def test_too_long_ai_output_falls_back() -> None:
    long = good_output().model_copy(update={"body": "word " * 61})
    result = explain(
        topic=Topic.PROJECTION,
        facts=parsed(Topic.PROJECTION),
        term=None,
        level="simple",
        language="en",
        explainer=fake_explainer(long),
        cache=ResponseCache(),
    )
    assert result.source == "fallback"


def test_api_error_falls_back() -> None:
    result = explain(
        topic=Topic.TERM,
        facts=None,
        term="bond",
        level="simple",
        language="en",
        explainer=fake_explainer(None),
        cache=ResponseCache(),
    )
    assert result.source == "fallback"
    assert result.title == "Bond"


def test_cache_returns_stored_response_on_identical_call() -> None:
    explainer = fake_explainer(good_output())
    cache = ResponseCache()
    kwargs: dict[str, Any] = {
        "topic": Topic.PROJECTION,
        "facts": parsed(Topic.PROJECTION),
        "term": None,
        "level": "simple",
        "language": "en",
        "explainer": explainer,
        "cache": cache,
    }
    first = explain(**kwargs)
    second = explain(**kwargs)
    assert first == second
    assert explainer.generate.call_count == 1


def test_openai_errors_become_none() -> None:
    import httpx
    import openai

    explainer = OpenAIExplainer("sk-test", "gpt-test", max_retries=0)
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    explainer._client.responses.parse = MagicMock(  # type: ignore[method-assign]
        side_effect=openai.APITimeoutError(request=request)
    )
    assert explainer.generate("prompt") is None


def test_projection_facts_reject_bad_values() -> None:
    with pytest.raises(ValueError):
        ProjectionFacts.model_validate(SAMPLE_FACTS[Topic.PROJECTION] | {"success_probability": 2})
    assert RiskProfile(SAMPLE_FACTS[Topic.PROJECTION]["profile"]) == RiskProfile.BALANCED


# --- HTTP ---


@pytest.fixture
def no_ai(client: TestClient) -> Iterator[TestClient]:
    explain_router.response_cache.clear()
    explain_router.rate_limiter.reset()
    app = client.app
    app.dependency_overrides[explain_router.get_explainer] = lambda: None  # type: ignore[attr-defined]
    yield client


def test_explain_endpoint_without_key_uses_fallback(no_ai: TestClient) -> None:
    response = no_ai.post(
        "/explain",
        json={"topic": "projection", "facts": SAMPLE_FACTS[Topic.PROJECTION], "language": "fr"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "fallback"
    assert "132 500 €" in body["body"]


def test_explain_endpoint_for_term(no_ai: TestClient) -> None:
    response = no_ai.post("/explain", json={"topic": "term", "term": "glide_path"})
    assert response.json()["title"] == "Glide path"


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"topic": "term", "term": "unicorn"}, "Unknown term 'unicorn'"),
        ({"topic": "projection"}, "needs facts"),
        ({"topic": "rebalance", "facts": {"largest_drift": 0.1}}, "Field required"),
        ({"topic": "rebalance", "facts": {"threshold": 0.05, "moved_cents": -1}}, "greater than"),
    ],
)
def test_explain_endpoint_validates_input(
    no_ai: TestClient, payload: dict[str, Any], message: str
) -> None:
    response = no_ai.post("/explain", json=payload)
    assert response.status_code == 422
    assert message in str(response.json()["detail"])


def test_explain_endpoint_is_rate_limited(no_ai: TestClient) -> None:
    explain_router.rate_limiter.limit = 3
    try:
        codes = [
            no_ai.post("/explain", json={"topic": "term", "term": "bond"}).status_code
            for _ in range(4)
        ]
    finally:
        explain_router.rate_limiter.limit = 60
    assert codes == [200, 200, 200, 429]
