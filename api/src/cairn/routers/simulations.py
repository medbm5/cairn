from datetime import date

from fastapi import APIRouter

from cairn.domain.dates import add_months
from cairn.domain.glide_path import glide_path_for
from cairn.domain.profiles import PROFILES
from cairn.domain.simulation import Allocation, SimulationResult, simulate
from cairn.domain.solver import SOLVER_PATHS, SOLVER_SEED, GoalInputs, Grid, Lever, Solution, solve
from cairn.schemas import (
    SimulationRequest,
    SimulationResponse,
    SimulationSolveRequest,
    SolveResponse,
    SolverOptionOut,
)

router = APIRouter(tags=["simulations"])


def simulation_response(result: SimulationResult, paths: int) -> SimulationResponse:
    bands = result.percentiles
    return SimulationResponse(
        seed=result.seed,
        paths=paths,
        months=result.months,
        p10=bands[10],
        p25=bands[25],
        p50=bands[50],
        p75=bands[75],
        p90=bands[90],
        contributed=result.contributed,
        success_probability=result.success_probability,
    )


def solve_response(solution: Solution, today: date) -> SolveResponse:
    return SolveResponse(
        target_probability=solution.target_probability,
        current_probability=solution.current_probability,
        seed=SOLVER_SEED,
        paths=SOLVER_PATHS,
        options=[
            SolverOptionOut(
                lever=option.lever,
                value=option.value,
                current=option.current,
                delta=option.delta,
                relative_change=option.relative_change,
                success_probability=option.success_probability,
                feasible=option.feasible,
                target_date=(
                    add_months(today, option.value) if option.lever == Lever.HORIZON else None
                ),
            )
            for option in solution.options
        ],
    )


@router.post("/simulations")
def run_simulation(body: SimulationRequest) -> SimulationResponse:
    allocation: Allocation = (
        glide_path_for(body.profile) if body.glide_path else PROFILES[body.profile].weights
    )
    result = simulate(
        initial_cents=body.initial_cents,
        monthly_contribution_cents=body.monthly_contribution_cents,
        horizon_months=body.horizon_months,
        allocation=allocation,
        target_cents=body.target_cents,
        paths=body.paths,
        seed=body.seed,
    )
    return simulation_response(result, body.paths)


@router.post("/simulations/solve")
def solve_simulation(body: SimulationSolveRequest) -> SolveResponse:
    """The goal solver for the simulator, whose inputs are not a saved goal."""
    inputs = GoalInputs(
        initial_cents=body.initial_cents,
        monthly_contribution_cents=body.monthly_contribution_cents,
        horizon_months=body.horizon_months,
        target_cents=body.target_cents,
        profile=body.profile,
    )
    grid = Grid(
        contribution_cents=body.contribution_step_cents,
        horizon_months=body.horizon_step_months,
        target_cents=body.target_step_cents,
        max_contribution_cents=body.max_contribution_cents,
    )
    return solve_response(solve(inputs, body.target_probability, grid=grid), date.today())
