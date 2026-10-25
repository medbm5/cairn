from collections.abc import Iterator
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from cairn.domain.profiles import RiskProfile
from cairn.explain.client import GeneratedExplanation, OpenAIExplainer
from cairn.explain.facts import (
    FACT_MODELS,
    FactsModel,
    ProjectionFacts,
    SolverFacts,
    SupportAnswerFacts,
    Topic,
)
from cairn.explain.fallbacks import fallback
from cairn.explain.glossary import GLOSSARY
from cairn.explain.guard import numbers_in, unknown_numbers
from cairn.explain.service import WORD_LIMITS, ResponseCache, build_prompt, explain
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
    Topic.SUPPORT_ANSWER: {
        "question": "Why did the balance go down in March?",
        "focus": "month_change",
        "year": 2026,
        "month": 3,
        "start_balance_cents": 2_000_000,
        "end_balance_cents": 1_771_234,
        "change_cents": -228_766,
        "market_effect_cents": -287_266,
        "deposits_cents": 60_000,
        "fees_cents": 1_500,
        "market_by_asset_cents": {
            "global_equity": -210_000,
            "emerging_equity": -80_000,
            "euro_gov_bonds": 2_600,
            "money_market": 134,
        },
        "rebalanced_this_month": True,
        "last_rebalance_year": 2026,
        "last_rebalance_month": 3,
        "last_rebalance_day": 28,
        "last_rebalance_moved_cents": 123_456,
    },
    Topic.SOLVER: {
        "target_cents": 100_000_00,
        "monthly_contribution_cents": 300_00,
        "horizon_months": 180,
        "current_probability": 0.0575,
        "target_probability": 0.8,
        "needed_monthly_contribution_cents": 442_00,
        "contribution_increase_cents": 142_00,
        "contribution_feasible": True,
        "probability_with_contribution": 0.8035,
        "needed_horizon_months": 243,
        "horizon_extension_months": 63,
        "needed_goal_year": 2047,
        "needed_goal_month": 1,
        "horizon_feasible": True,
        "probability_with_horizon": 0.8045,
        "reachable_target_cents": 70_200_00,
        "target_reduction_cents": 29_800_00,
        "target_feasible": True,
        "probability_with_target": 0.8025,
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
    assert '"p50_eur":132500.0' in prompt and "WORD LIMIT FOR BODY: 60" in prompt
    assert "_cents" not in prompt  # the model never has to convert cents


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


# --- Support answers ---


def test_support_facts_must_add_up() -> None:
    sample = SAMPLE_FACTS[Topic.SUPPORT_ANSWER]
    with pytest.raises(ValueError, match="add up to the change"):
        SupportAnswerFacts.model_validate(sample | {"fees_cents": 1_501})
    with pytest.raises(ValueError, match="end minus start"):
        SupportAnswerFacts.model_validate(sample | {"end_balance_cents": 1_771_235})


@pytest.mark.parametrize("language", ["en", "fr"])
def test_support_fallback_states_every_part_to_the_cent(language: str) -> None:
    facts = parsed(Topic.SUPPORT_ANSWER)
    text = fallback(Topic.SUPPORT_ANSWER, facts, None, "simple", language)  # type: ignore[arg-type]
    expected = (
        ["€2,287.66", "-€2,872.66", "€600.00", "-€15.00"]
        if language == "en"
        else ["2 287,66 €", "-2 872,66 €", "600,00 €", "-15,00 €"]
    )
    for figure in expected:
        assert figure in text.body


def test_support_fallback_for_the_last_rebalance() -> None:
    facts = SupportAnswerFacts.model_validate(
        SAMPLE_FACTS[Topic.SUPPORT_ANSWER] | {"focus": "last_rebalance"}
    )
    text = fallback(Topic.SUPPORT_ANSWER, facts, None, "simple", "en")
    assert "28 March 2026" in text.body and "€1,234.56" in text.body
    assert unknown_numbers(text.body, facts) == []
    none_yet = SupportAnswerFacts.model_validate(
        SAMPLE_FACTS[Topic.SUPPORT_ANSWER]
        | {"focus": "last_rebalance", "last_rebalance_year": None, "last_rebalance_month": None}
    )
    assert "no rebalance" in fallback(Topic.SUPPORT_ANSWER, none_yet, None, "simple", "en").body


def test_guard_reads_losses_without_their_sign() -> None:
    facts = parsed(Topic.SUPPORT_ANSWER)
    assert unknown_numbers("Markets took away €2,872.66 and global shares €2,100.", facts) == []
    assert unknown_numbers("Markets took away €3,000.", facts) == [3000.0]


def test_support_prompt_asks_for_the_split() -> None:
    explainer = fake_explainer(None)
    explain(
        topic=Topic.SUPPORT_ANSWER,
        facts=parsed(Topic.SUPPORT_ANSWER),
        term=None,
        level="simple",
        language="en",
        explainer=explainer,
        cache=ResponseCache(),
    )
    prompt = explainer.generate.call_args.args[0]
    assert "SUPPORT ANSWER" in prompt and "market effect, deposits, fees" in prompt


# --- Goal solver ---


def test_solver_facts_must_be_consistent() -> None:
    sample = SAMPLE_FACTS[Topic.SOLVER]
    with pytest.raises(ValueError, match="new value minus the current"):
        SolverFacts.model_validate(sample | {"contribution_increase_cents": 100_00})


@pytest.mark.parametrize("language", ["en", "fr"])
def test_solver_fallback_lists_every_feasible_option(language: str) -> None:
    text = fallback(Topic.SOLVER, parsed(Topic.SOLVER), None, "simple", language)  # type: ignore[arg-type]
    if language == "en":
        assert "saving €442 a month" in text.body
        assert "moving the date to January 2047" in text.body
        assert "aiming for €70,200" in text.body
    else:
        assert "442 €" in text.body and "janvier 2047" in text.body and "70 200 €" in text.body


def test_solver_fallback_leaves_out_what_is_out_of_reach() -> None:
    out_of_reach = {
        "horizon_feasible": False,
        "needed_horizon_months": 480,
        "horizon_extension_months": 300,
        "needed_goal_year": 2066,
    }
    facts = SolverFacts.model_validate(SAMPLE_FACTS[Topic.SOLVER] | out_of_reach)
    text = fallback(Topic.SOLVER, facts, None, "simple", "en")
    assert "2066" not in text.body
    assert "Even 40 years would not be enough" in text.body
    assert unknown_numbers(text.body, facts) == []


def test_solver_prompt_presents_options_without_advice() -> None:
    prompt = build_prompt(Topic.SOLVER, parsed(Topic.SOLVER), None, "simple", "en", [])
    assert "never say which to choose" in prompt
    assert '"needed_monthly_contribution_eur":442.0' in prompt
