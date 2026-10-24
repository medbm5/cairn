from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from cairn.db import get_session
from cairn.models import Goal
from cairn.routers.simulations import simulation_response
from cairn.schemas import GoalCreate, GoalOut, GoalProjection, GoalUpdate
from cairn.services import goals as service
from cairn.services import ledger

router = APIRouter(prefix="/goals", tags=["goals"])

SessionDep = Annotated[Session, Depends(get_session)]


def goal_or_404(session: SessionDep, goal_id: int) -> Goal:
    try:
        return service.get_goal(session, goal_id)
    except service.GoalNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


GoalDep = Annotated[Goal, Depends(goal_or_404)]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_goal(body: GoalCreate, session: SessionDep) -> GoalOut:
    return GoalOut.model_validate(service.create_goal(session, body))


@router.get("")
def list_goals(session: SessionDep) -> list[GoalOut]:
    return [GoalOut.model_validate(goal) for goal in service.list_goals(session)]


@router.get("/{goal_id}")
def get_goal(goal: GoalDep) -> GoalOut:
    return GoalOut.model_validate(goal)


@router.patch("/{goal_id}")
def update_goal(goal: GoalDep, body: GoalUpdate, session: SessionDep) -> GoalOut:
    return GoalOut.model_validate(service.update_goal(session, goal.id, body))


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(goal: GoalDep, session: SessionDep) -> Response:
    service.delete_goal(session, goal.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{goal_id}/projection")
def goal_projection(
    goal: GoalDep,
    session: SessionDep,
    seed: Annotated[int | None, Query(ge=0, le=2**32 - 1)] = None,
    paths: Annotated[int, Query(ge=100, le=10_000)] = 5_000,
) -> GoalProjection:
    start_cents = sum(ledger.holdings(session, goal).values())
    horizon, result = service.project_goal(
        goal, start_cents=start_cents, today=date.today(), seed=seed, paths=paths
    )
    return GoalProjection(
        goal_id=goal.id,
        horizon_months=horizon,
        start_cents=start_cents,
        target_cents=goal.target_cents,
        simulation=simulation_response(result, paths),
    )
