import itertools
import math
import time

from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st

from cairn.domain.profiles import (
    ASSUMPTIONS,
    PROFILES,
    AssetAssumption,
    AssetClass,
    RiskProfile,
)
from cairn.domain.simulation import PERCENTILES, simulate

BALANCED = PROFILES[RiskProfile.BALANCED].weights


def test_zero_volatility_matches_compound_interest() -> None:
    flat = {a: AssetAssumption(expected_return=0.05, volatility=0.0) for a in ASSUMPTIONS}
    result = simulate(
        initial_cents=1_000_000,
        monthly_contribution_cents=10_000,
        horizon_months=120,
        allocation=BALANCED,
        paths=200,
        seed=1,
        assumptions=flat,
    )
    monthly_growth = 1.05 ** (1 / 12)
    expected = 1_000_000.0
    for _ in range(120):
        expected = expected * monthly_growth + 10_000
    for p in PERCENTILES:
        assert math.isclose(result.percentiles[p][-1], expected, abs_tol=1)


def test_same_seed_gives_identical_results() -> None:
    kwargs = {
        "initial_cents": 500_000,
        "monthly_contribution_cents": 20_000,
        "horizon_months": 60,
        "allocation": BALANCED,
        "target_cents": 2_000_000,
        "paths": 1_000,
        "seed": 42,
    }
    assert simulate(**kwargs) == simulate(**kwargs)  # type: ignore[arg-type]


def test_seed_is_generated_and_returned() -> None:
    result = simulate(
        initial_cents=100, monthly_contribution_cents=0, horizon_months=12, allocation=BALANCED
    )
    assert isinstance(result.seed, int)


@given(
    initial=st.integers(0, 10_000_000),
    monthly=st.integers(0, 500_000),
    months=st.integers(12, 240),
    seed=st.integers(0, 2**32 - 1),
)
@settings(max_examples=30, deadline=None)
def test_percentiles_are_ordered(initial: int, monthly: int, months: int, seed: int) -> None:
    result = simulate(
        initial_cents=initial,
        monthly_contribution_cents=monthly,
        horizon_months=months,
        allocation=PROFILES[RiskProfile.BOLD].weights,
        paths=300,
        seed=seed,
    )
    for lower, upper in itertools.pairwise(PERCENTILES):
        assert all(
            a <= b
            for a, b in zip(result.percentiles[lower], result.percentiles[upper], strict=True)
        )


@given(
    monthly=st.integers(0, 200_000),
    extra=st.integers(1, 200_000),
    target=st.integers(0, 50_000_000),
    seed=st.integers(0, 2**32 - 1),
)
@settings(max_examples=30, deadline=None)
def test_higher_contribution_never_lowers_success(
    monthly: int, extra: int, target: int, seed: int
) -> None:
    def success(contribution: int) -> float:
        result = simulate(
            initial_cents=100_000,
            monthly_contribution_cents=contribution,
            horizon_months=120,
            allocation=BALANCED,
            target_cents=target,
            paths=300,
            seed=seed,
        )
        assert result.success_probability is not None
        return result.success_probability

    assert success(monthly + extra) >= success(monthly)


def test_full_size_simulation_is_fast() -> None:
    # Budget is 150 ms on a laptop; the bound here is generous so CI machines do not flake.
    simulate(initial_cents=0, monthly_contribution_cents=1, horizon_months=12, allocation=BALANCED)
    started = time.perf_counter()
    simulate(
        initial_cents=1_000_000,
        monthly_contribution_cents=50_000,
        horizon_months=480,
        allocation=BALANCED,
        target_cents=50_000_000,
        paths=5_000,
        seed=7,
    )
    assert time.perf_counter() - started < 1.0


def test_simulation_endpoint(client: TestClient) -> None:
    body = {
        "initial_cents": 1_000_000,
        "monthly_contribution_cents": 30_000,
        "horizon_months": 240,
        "profile": "balanced",
        "target_cents": 10_000_000,
        "seed": 123,
        "paths": 1_000,
    }
    first = client.post("/simulations", json=body).json()
    second = client.post("/simulations", json=body).json()
    assert first == second
    assert first["seed"] == 123
    assert len(first["p50"]) == 241
    assert first["contributed"][-1] == 1_000_000 + 30_000 * 240
    assert 0 <= first["success_probability"] <= 1


def test_simulation_endpoint_validates_horizon(client: TestClient) -> None:
    body = {
        "initial_cents": 0,
        "monthly_contribution_cents": 0,
        "horizon_months": 600,
        "profile": "bold",
    }
    response = client.post("/simulations", json=body)
    assert response.status_code == 422


def test_asset_classes_cover_assumptions() -> None:
    assert set(ASSUMPTIONS) == set(AssetClass)
