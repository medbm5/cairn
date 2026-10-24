import math

import pytest
from fastapi.testclient import TestClient
from hypothesis import given
from hypothesis import strategies as st

from cairn.domain import profiles as p


def test_weights_sum_to_one_for_every_profile() -> None:
    for profile, info in p.PROFILES.items():
        assert math.isclose(sum(info.weights.values()), 1.0), profile
        assert set(info.weights) == set(p.ASSET_CLASSES)
        assert all(w >= 0 for w in info.weights.values())


def test_equity_share_increases_with_risk() -> None:
    shares = [p.equity_share(p.PROFILES[profile].weights) for profile in p.PROFILE_ORDER]
    assert shares == sorted(shares)


def test_correlation_matrix_is_symmetric_with_unit_diagonal() -> None:
    n = len(p.ASSET_CLASSES)
    for i in range(n):
        assert p.CORRELATIONS[i][i] == 1.0
        for j in range(n):
            assert p.CORRELATIONS[i][j] == p.CORRELATIONS[j][i]


def test_option_scores_are_ordered_within_each_question() -> None:
    for question in p.QUESTIONS:
        scores = [o.score for o in question.options]
        assert scores == sorted(scores), question.id


# Each answer set is a list of option indexes (one per question); higher index = more tolerant.
option_indexes = st.tuples(*(st.integers(0, len(q.options) - 1) for q in p.QUESTIONS))


def _answers(indexes: tuple[int, ...]) -> dict[str, str]:
    return {q.id: q.options[i].id for q, i in zip(p.QUESTIONS, indexes, strict=True)}


@given(base=option_indexes, data=st.data())
def test_scoring_is_monotonic(base: tuple[int, ...], data: st.DataObject) -> None:
    # Raise some answers to a more risk-tolerant option; the profile must never get more prudent.
    raised = tuple(
        data.draw(st.integers(i, len(q.options) - 1))
        for q, i in zip(p.QUESTIONS, base, strict=True)
    )
    before = p.PROFILE_ORDER.index(p.score_questionnaire(_answers(base)))
    after = p.PROFILE_ORDER.index(p.score_questionnaire(_answers(raised)))
    assert after >= before


def test_extreme_answers_map_to_extreme_profiles() -> None:
    lowest = {q.id: q.options[0].id for q in p.QUESTIONS}
    highest = {q.id: q.options[-1].id for q in p.QUESTIONS}
    assert p.score_questionnaire(lowest) == p.RiskProfile.PRUDENT
    assert p.score_questionnaire(highest) == p.RiskProfile.BOLD


def test_missing_answer_is_rejected() -> None:
    with pytest.raises(p.QuestionnaireError, match="Missing"):
        p.score_questionnaire({"horizon": "gt20"})


def test_profiles_endpoint(client: TestClient) -> None:
    body = client.get("/profiles").json()
    assert [item["key"] for item in body] == ["prudent", "moderate", "balanced", "dynamic", "bold"]


def test_questionnaire_endpoint_in_french(client: TestClient) -> None:
    body = client.get("/questionnaire", params={"language": "fr"}).json()
    assert len(body) == 6
    assert body[0]["text"] == "Quand aurez-vous besoin de cet argent ?"


def test_score_endpoint(client: TestClient) -> None:
    answers = {q.id: q.options[-1].id for q in p.QUESTIONS}
    response = client.post("/questionnaire/score", json={"answers": answers})
    assert response.status_code == 200
    assert response.json()["profile"]["key"] == "bold"


def test_score_endpoint_rejects_unknown_option(client: TestClient) -> None:
    answers = {q.id: q.options[0].id for q in p.QUESTIONS} | {"horizon": "tomorrow"}
    response = client.post("/questionnaire/score", json={"answers": answers})
    assert response.status_code == 422
    assert "tomorrow" in response.json()["detail"]
