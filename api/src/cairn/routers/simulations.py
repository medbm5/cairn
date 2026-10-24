from fastapi import APIRouter

from cairn.domain.profiles import PROFILES
from cairn.domain.simulation import SimulationResult, simulate
from cairn.schemas import SimulationRequest, SimulationResponse

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


@router.post("/simulations")
def run_simulation(body: SimulationRequest) -> SimulationResponse:
    result = simulate(
        initial_cents=body.initial_cents,
        monthly_contribution_cents=body.monthly_contribution_cents,
        horizon_months=body.horizon_months,
        allocation=PROFILES[body.profile].weights,
        target_cents=body.target_cents,
        paths=body.paths,
        seed=body.seed,
    )
    return simulation_response(result, body.paths)
