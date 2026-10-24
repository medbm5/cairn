"""Seed the demo: the demo user, three goals and 24 months of history.

Everything goes through the services (deposits, market movements, rebalances), so the ledger is
built exactly as in production and always reconciles. Safe to run twice: goals are matched by
name and every posting has an idempotency key, so a second run adds nothing.

Run from api/:  uv run python scripts/seed.py
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from cairn.db import get_sessionmaker
from cairn.domain.profiles import RiskProfile
from cairn.models import Goal
from cairn.schemas import GoalType
from cairn.services import ledger
from cairn.services.goals import demo_user

HISTORY_MONTHS = 24


@dataclass(frozen=True)
class DemoGoal:
    name: str
    type: GoalType
    profile: RiskProfile
    target_cents: int
    years_left: int
    initial_cents: int
    monthly_cents: int


DEMO_GOALS = (
    DemoGoal(
        "Retirement", GoalType.RETIREMENT, RiskProfile.BOLD, 250_000_00, 25, 10_000_00, 400_00
    ),
    DemoGoal("A flat in Lyon", GoalType.HOME, RiskProfile.BALANCED, 60_000_00, 7, 5_000_00, 500_00),
    DemoGoal(
        "Safety net", GoalType.SAFETY_NET, RiskProfile.PRUDENT, 10_000_00, 2, 1_000_00, 250_00
    ),
)


def add_months(day: date, months: int) -> date:
    total = day.year * 12 + day.month - 1 + months
    return date(total // 12, total % 12 + 1, min(day.day, 28))


def get_or_create_goal(session: Session, spec: DemoGoal, today: date) -> Goal:
    goal = session.scalars(select(Goal).where(Goal.name == spec.name)).first()
    if goal is None:
        goal = Goal(
            user_id=demo_user(session).id,
            name=spec.name,
            type=spec.type,
            profile=spec.profile,
            target_cents=spec.target_cents,
            target_date=add_months(today, spec.years_left * 12),
            monthly_contribution_cents=spec.monthly_cents,
        )
        session.add(goal)
        session.commit()
    return goal


def seed_goal_history(session: Session, goal: Goal, spec: DemoGoal, today: date) -> None:
    """Replay the last 24 months: a deposit, the month's market movement, and a rebalance check."""
    start = add_months(today.replace(day=1), -HISTORY_MONTHS)
    for i in range(HISTORY_MONTHS):
        day = add_months(start, i)
        key = f"seed-{day:%Y-%m}"
        # A replayed month is complete: re-checking drift now would use today's holdings.
        if ledger.find_entry(session, f"deposit:{goal.id}:{key}") is not None:
            continue
        at = datetime(day.year, day.month, 1, 9, 0, tzinfo=UTC)
        amount = spec.initial_cents + spec.monthly_cents if i == 0 else spec.monthly_cents
        ledger.deposit(session, goal, amount, key, today=day, created_at=at)
        month_end = datetime(day.year, day.month, 28, 17, 0, tzinfo=UTC)
        ledger.mark_to_market(session, goal, day.year, day.month, created_at=month_end)
        ledger.rebalance(session, goal, as_of=day.replace(day=28), created_at=month_end)


def seed(session: Session, today: date) -> list[Goal]:
    goals = []
    for spec in DEMO_GOALS:
        goal = get_or_create_goal(session, spec, today)
        seed_goal_history(session, goal, spec, today)
        goals.append(goal)
    return goals


def main() -> None:
    with get_sessionmaker()() as session:
        goals = seed(session, date.today())
        result = ledger.reconcile(session)
        print(f"Seeded {len(goals)} goals. Ledger reconciled: {result.ok}")
        if not result.ok:
            raise SystemExit("Reconciliation failed after seeding.")


if __name__ == "__main__":
    main()
