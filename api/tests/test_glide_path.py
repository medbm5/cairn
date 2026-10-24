import math

from fastapi.testclient import TestClient
from hypothesis import given
from hypothesis import strategies as st

from cairn.domain.glide_path import (
    GLIDE_MONTHS,
    PRESERVATION_MIX,
    allocation_at,
    glide_path_for,
)
from cairn.domain.profiles import PROFILES, RiskProfile, equity_share
from cairn.domain.simulation import SimulationResult, simulate

profiles = st.sampled_from(list(RiskProfile))


@given(profile=profiles, months=st.integers(0, 600))
def test_equity_never_increases_as_goal_approaches(profile: RiskProfile, months: int) -> None:
    if months == 0:
        return
    later = equity_share(allocation_at(profile, months - 1))
    earlier = equity_share(allocation_at(profile, months))
    assert later <= earlier + 1e-12


@given(profile=profiles, months=st.integers(-12, 600))
def test_weights_always_sum_to_one(profile: RiskProfile, months: int) -> None:
    weights = allocation_at(profile, months)
    assert math.isclose(sum(weights.values()), 1.0)
    assert all(w >= 0 for w in weights.values())


def test_preservation_mix_at_goal_date() -> None:
    for profile in RiskProfile:
        assert allocation_at(profile, 0) == PRESERVATION_MIX


def test_full_profile_risk_with_ten_years_or_more() -> None:
    for profile in RiskProfile:
        assert allocation_at(profile, GLIDE_MONTHS) == PROFILES[profile].weights
        assert allocation_at(profile, 400) == PROFILES[profile].weights


def test_glide_path_narrows_the_final_range() -> None:
    common = {
        "initial_cents": 1_000_000,
        "monthly_contribution_cents": 20_000,
        "horizon_months": 180,
        "paths": 2_000,
        "seed": 3,
    }
    fixed = simulate(allocation=PROFILES[RiskProfile.BOLD].weights, **common)  # type: ignore[arg-type]
    glided = simulate(allocation=glide_path_for(RiskProfile.BOLD), **common)  # type: ignore[arg-type]

    def spread(result: SimulationResult) -> int:
        return result.percentiles[90][-1] - result.percentiles[10][-1]

    assert spread(glided) < spread(fixed)


def test_glide_path_endpoint(client: TestClient) -> None:
    response = client.get("/glide-path", params={"profile": "dynamic", "horizon_months": 180})
    assert response.status_code == 200
    points = response.json()["points"]
    assert [p["year"] for p in points] == list(range(16))
    assert points[0]["months_remaining"] == 180
    assert points[-1]["months_remaining"] == 0
    assert points[-1]["equity_share"] == 0.1


def test_simulation_endpoint_accepts_glide_path(client: TestClient) -> None:
    body = {
        "initial_cents": 100_000,
        "monthly_contribution_cents": 10_000,
        "horizon_months": 60,
        "profile": "bold",
        "glide_path": True,
        "seed": 9,
        "paths": 500,
    }
    assert client.post("/simulations", json=body).status_code == 200
