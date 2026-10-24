"""Goal use cases: CRUD for the demo user, and the glide-path projection of a goal."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from cairn.domain.dates import months_between
from cairn.domain.glide_path import glide_path_for
from cairn.domain.profiles import RiskProfile
from cairn.domain.simulation import SimulationResult, simulate
from cairn.models import Goal, User
from cairn.schemas import GoalCreate, GoalUpdate

DEMO_USER_NAME = "Demo user"


class GoalNotFoundError(LookupError):
    def __init__(self, goal_id: int) -> None:
        super().__init__(f"Goal {goal_id} does not exist.")


def demo_user(session: Session) -> User:
    user = session.scalars(select(User).order_by(User.id).limit(1)).first()
    if user is None:
        user = User(name=DEMO_USER_NAME)
        session.add(user)
        session.flush()
    return user


def create_goal(session: Session, data: GoalCreate) -> Goal:
    goal = Goal(user_id=demo_user(session).id, **data.model_dump())
    session.add(goal)
    session.commit()
    return goal


def list_goals(session: Session) -> list[Goal]:
    return list(session.scalars(select(Goal).order_by(Goal.id)))


def get_goal(session: Session, goal_id: int) -> Goal:
    goal = session.get(Goal, goal_id)
    if goal is None:
        raise GoalNotFoundError(goal_id)
    return goal


def update_goal(session: Session, goal_id: int, data: GoalUpdate) -> Goal:
    goal = get_goal(session, goal_id)
    for field, value in data.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(goal, field, value)
    session.commit()
    return goal


def delete_goal(session: Session, goal_id: int) -> None:
    session.delete(get_goal(session, goal_id))
    session.commit()


def project_goal(
    goal: Goal,
    *,
    start_cents: int,
    today: date,
    seed: int | None = None,
    paths: int = 5_000,
) -> tuple[int, SimulationResult]:
    """Run the glide-path simulation from today to the goal date. Returns (horizon, result)."""
    horizon = max(months_between(today, goal.target_date), 1)
    result = simulate(
        initial_cents=start_cents,
        monthly_contribution_cents=goal.monthly_contribution_cents,
        horizon_months=horizon,
        allocation=glide_path_for(RiskProfile(goal.profile)),
        target_cents=goal.target_cents,
        paths=paths,
        seed=goal.id if seed is None else seed,  # stable per goal unless asked otherwise
    )
    return horizon, result
