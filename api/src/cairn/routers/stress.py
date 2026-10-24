from dataclasses import asdict
from datetime import date

from fastapi import APIRouter

from cairn.domain.stress import SCENARIOS, Scenario, replay
from cairn.routers.goals import GoalDep, SessionDep
from cairn.schemas import ReplayOut, StressTestOut
from cairn.services import ledger

router = APIRouter(tags=["stress tests"])

# Used when a goal has no money yet, so the replay still shows the shape of the scenario.
NOTIONAL_CENTS = 10_000_00


@router.post("/goals/{goal_id}/stress-tests/{scenario}")
def run_stress_test(goal: GoalDep, scenario: Scenario, session: SessionDep) -> StressTestOut:
    weights = ledger.current_allocation(goal, date.today())
    start = sum(ledger.holdings(session, goal).values()) or NOTIONAL_CENTS
    info = SCENARIOS[scenario]
    return StressTestOut(
        scenario=scenario,
        name=info.name,
        description=info.description,
        months=info.months,
        start_cents=start,
        weights={a: round(w, 4) for a, w in weights.items()},
        without_rebalancing=ReplayOut(**asdict(replay(scenario, weights, start, rebalance=False))),
        with_rebalancing=ReplayOut(**asdict(replay(scenario, weights, start, rebalance=True))),
    )
