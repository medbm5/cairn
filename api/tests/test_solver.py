import time
from dataclasses import replace
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cairn.domain.dates import add_months, months_between
from cairn.domain.glide_path import glide_path_for
from cairn.domain.profiles import RiskProfile
from cairn.domain.simulation import simulate
from cairn.domain.solver import (
    MAX_HORIZON_MONTHS,
    SOLVER_PATHS,
    SOLVER_SEED,
    GoalInputs,
    Grid,
    Lever,
    solve,
    solve_horizon,
    solve_monthly_contribution,
    solve_target,
    success_probability,
)
from cairn.explain.facts import SolverFacts, solver_facts
from tests.factories import make_goal

# The landing page's example: €5,000 to start, €300 a month, €100,000 in 15 years.
EXAMPLE = GoalInputs(
    initial_cents=5_000_00,
    monthly_contribution_cents=300_00,
    horizon_months=180,
    target_cents=100_000_00,
    profile=RiskProfile.BALANCED,
)


def test_solver_measures_chance_like_the_simulation() -> None:
    result = simulate(
        initial_cents=EXAMPLE.initial_cents,
        monthly_contribution_cents=EXAMPLE.monthly_contribution_cents,
        horizon_months=EXAMPLE.horizon_months,
        allocation=glide_path_for(EXAMPLE.profile),
        target_cents=EXAMPLE.target_cents,
        paths=SOLVER_PATHS,
        seed=SOLVER_SEED,
    )
    assert result.success_probability is not None
    assert abs(success_probability(EXAMPLE) - result.success_probability) <= 1 / SOLVER_PATHS


def test_contribution_reaches_the_target_and_one_euro_less_does_not() -> None:
    option = solve_monthly_contribution(EXAMPLE)
    assert option.feasible
    assert option.value % 100 == 0
    assert option.success_probability >= 0.8
    one_euro_less = replace(EXAMPLE, monthly_contribution_cents=option.value - 100)
    assert success_probability(one_euro_less) < 0.8
    assert success_probability(replace(EXAMPLE, monthly_contribution_cents=option.value)) >= 0.8


@pytest.mark.parametrize("profile", list(RiskProfile))
def test_higher_target_probability_never_lowers_the_contribution(profile: RiskProfile) -> None:
    inputs = replace(EXAMPLE, profile=profile)
    needed = [solve_monthly_contribution(inputs, p).value for p in (0.5, 0.6, 0.7, 0.8, 0.9, 0.95)]
    assert needed == sorted(needed)


def test_horizon_reaches_the_target_with_the_same_contribution() -> None:
    option = solve_horizon(EXAMPLE)
    assert option.feasible
    assert option.value > EXAMPLE.horizon_months
    assert success_probability(replace(EXAMPLE, horizon_months=option.value)) >= 0.8
    assert success_probability(replace(EXAMPLE, horizon_months=option.value - 1)) < 0.8


def test_target_is_the_largest_reachable_in_hundreds_of_euros() -> None:
    option = solve_target(EXAMPLE)
    assert option.feasible
    assert option.value % 100_00 == 0
    assert option.value < EXAMPLE.target_cents
    assert success_probability(replace(EXAMPLE, target_cents=option.value)) >= 0.8
    assert success_probability(replace(EXAMPLE, target_cents=option.value + 100_00)) < 0.8


def test_out_of_reach_levers_are_not_feasible() -> None:
    # Nothing saved, nothing invested: no date will ever reach the target.
    nothing = replace(EXAMPLE, initial_cents=0, monthly_contribution_cents=0)
    horizon = solve_horizon(nothing)
    assert not horizon.feasible
    assert horizon.value == MAX_HORIZON_MONTHS
    assert not solve_target(nothing).feasible
    # A contribution cap too low for the target.
    capped = solve_monthly_contribution(EXAMPLE, grid=Grid(max_contribution_cents=100_00))
    assert not capped.feasible
    assert capped.value == 100_00


def test_a_goal_already_on_track_needs_no_change_upward() -> None:
    easy = replace(EXAMPLE, target_cents=10_000_00)
    assert solve_monthly_contribution(easy).value <= easy.monthly_contribution_cents
    assert solve_target(easy).value >= easy.target_cents


def test_answers_snap_to_the_grid() -> None:
    grid = Grid(contribution_cents=25_00, horizon_months=12, target_cents=5_000_00)
    solution = solve(EXAMPLE, grid=grid)
    by_lever = {option.lever: option for option in solution.options}
    assert by_lever[Lever.CONTRIBUTION].value % 25_00 == 0
    assert by_lever[Lever.HORIZON].value % 12 == 0
    assert by_lever[Lever.TARGET].value % 5_000_00 == 0


def test_same_inputs_give_identical_outputs() -> None:
    assert solve(EXAMPLE) == solve(EXAMPLE)


def test_options_are_sorted_by_smallest_relative_change() -> None:
    options = solve(EXAMPLE).options
    assert {option.lever for option in options} == set(Lever)
    changes = [option.relative_change for option in options]
    assert changes == sorted(changes)


def test_all_three_levers_take_under_a_second() -> None:
    solve(EXAMPLE)  # warm up NumPy
    longest = replace(EXAMPLE, horizon_months=MAX_HORIZON_MONTHS - 12, target_cents=10**10)
    started = time.perf_counter()
    solve(longest)
    solve(EXAMPLE)
    assert (time.perf_counter() - started) / 2 < 1.0


def test_add_months_round_trips_with_months_between() -> None:
    for start in (date(2026, 1, 31), date(2026, 3, 31), date(2024, 2, 29), date(2026, 10, 25)):
        for months in range(0, MAX_HORIZON_MONTHS + 1):
            assert months_between(start, add_months(start, months)) == months


def test_solver_facts_are_built_from_the_solution() -> None:
    solution = solve(EXAMPLE)
    facts = solver_facts(solution, EXAMPLE, date(2047, 1, 1))
    assert isinstance(facts, SolverFacts)
    assert facts.current_probability == solution.current_probability
    assert facts.needed_goal_year == 2047


# --- Endpoints ---


def test_goal_solve_endpoint(client: TestClient, session: Session) -> None:
    goal = make_goal(session)
    response = client.post(f"/goals/{goal.id}/solve")
    assert response.status_code == 200
    body = response.json()
    assert body["target_probability"] == 0.8
    assert body["seed"] == SOLVER_SEED and body["paths"] == SOLVER_PATHS
    assert [o["lever"] for o in body["options"]] != []
    changes = [o["relative_change"] for o in body["options"] if o["feasible"]]
    assert changes == sorted(changes)
    horizon = next(o for o in body["options"] if o["lever"] == "horizon")
    assert (
        months_between(date.today(), date.fromisoformat(horizon["target_date"]))
        == (horizon["value"])
    )
    assert all(o["target_date"] is None for o in body["options"] if o["lever"] != "horizon")


def test_goal_solve_accepts_a_target_probability(client: TestClient, session: Session) -> None:
    goal = make_goal(session)
    low = client.post(f"/goals/{goal.id}/solve", json={"target_probability": 0.5}).json()
    high = client.post(f"/goals/{goal.id}/solve", json={"target_probability": 0.95}).json()

    def contribution(body: dict[str, list[dict[str, int]]]) -> int:
        return next(o["value"] for o in body["options"] if o["lever"] == "contribution")

    assert contribution(low) <= contribution(high)
    for bad in (0.3, 0.99):
        response = client.post(f"/goals/{goal.id}/solve", json={"target_probability": bad})
        assert response.status_code == 422


def test_goal_solve_unknown_goal_returns_404(client: TestClient) -> None:
    assert client.post("/goals/9999/solve").status_code == 404


def test_simulation_solve_endpoint_snaps_to_the_sliders(client: TestClient) -> None:
    response = client.post(
        "/simulations/solve",
        json={
            "initial_cents": 5_000_00,
            "monthly_contribution_cents": 300_00,
            "horizon_months": 180,
            "profile": "balanced",
            "target_cents": 100_000_00,
            "contribution_step_cents": 25_00,
            "horizon_step_months": 12,
            "target_step_cents": 5_000_00,
            "max_contribution_cents": 3_000_00,
        },
    )
    assert response.status_code == 200
    by_lever = {o["lever"]: o for o in response.json()["options"]}
    assert by_lever["contribution"]["value"] % 25_00 == 0
    assert by_lever["horizon"]["value"] % 12 == 0
    assert by_lever["target"]["value"] % 5_000_00 == 0
    assert by_lever["contribution"]["value"] <= 3_000_00
