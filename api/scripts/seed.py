"""Seed the demo: the demo user with three goals, and five clients for the support view.

Everything goes through the services (deposits, fees, market movements, rebalances), so the ledger
is built exactly as in production and always reconciles. Safe to run twice: clients are matched by
email, goals by owner and name, and every posting has an idempotency key, so a second run adds
nothing.

Run from api/:  uv run python scripts/seed.py
With --if-empty the demo user's goals are only seeded when no goal exists yet (used on Render, so
visitors' changes survive a redeploy); the support clients are always brought up to date.
"""

import sys
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from cairn.db import get_sessionmaker
from cairn.domain.profiles import AssetClass, RiskProfile
from cairn.models import Goal, User
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
    history_months: int = HISTORY_MONTHS
    deposit_every: int = 1  # months between deposits after the first one
    quarterly_fee_cents: int = 0  # taken at the end of March, June, September and December
    # A staged market shock: these returns replace the seeded ones, `shock_months_ago` months back.
    shock_months_ago: int | None = None
    shock: Mapping[AssetClass, float] | None = None


@dataclass(frozen=True)
class DemoClient:
    name: str
    email: str
    goals: tuple[DemoGoal, ...]


# An equity crash in one month, of the size seen in March 2020; bonds and cash barely move.
CRASH: Mapping[AssetClass, float] = {
    AssetClass.GLOBAL_EQUITY: -0.17,
    AssetClass.EMERGING_EQUITY: -0.23,
    AssetClass.EURO_GOV_BONDS: 0.012,
    AssetClass.MONEY_MARKET: 0.001,
}

DEMO_GOALS = (
    DemoGoal(
        "Retirement", GoalType.RETIREMENT, RiskProfile.BOLD, 250_000_00, 25, 10_000_00, 400_00
    ),
    DemoGoal("A flat in Lyon", GoalType.HOME, RiskProfile.BALANCED, 60_000_00, 7, 5_000_00, 500_00),
    DemoGoal(
        "Safety net", GoalType.SAFETY_NET, RiskProfile.PRUDENT, 10_000_00, 2, 1_000_00, 250_00
    ),
)

# Invented people for the support view (example.com addresses are reserved for examples).
SUPPORT_CLIENTS = (
    DemoClient(
        "Camille Martin",
        "camille.martin@example.com",
        (
            DemoGoal(
                "A flat in Nantes",
                GoalType.HOME,
                RiskProfile.DYNAMIC,
                80_000_00,
                6,
                8_000_00,
                600_00,
                quarterly_fee_cents=15_00,
                shock_months_ago=7,
                shock=CRASH,
            ),
        ),
    ),
    DemoClient(
        "Thomas Bernard",
        "thomas.bernard@example.com",
        (
            DemoGoal(
                "Retirement",
                GoalType.RETIREMENT,
                RiskProfile.BOLD,
                400_000_00,
                28,
                20_000_00,
                900_00,
                history_months=30,
                deposit_every=3,
                quarterly_fee_cents=25_00,
            ),
            DemoGoal(
                "Studies for the children",
                GoalType.STUDIES,
                RiskProfile.MODERATE,
                40_000_00,
                12,
                2_000_00,
                150_00,
                history_months=18,
            ),
        ),
    ),
    DemoClient(
        "Léa Dubois",
        "lea.dubois@example.com",
        (
            DemoGoal(
                "Safety net",
                GoalType.SAFETY_NET,
                RiskProfile.PRUDENT,
                6_000_00,
                1,
                500_00,
                200_00,
                history_months=12,
            ),
        ),
    ),
    DemoClient(
        "Hugo Petit",
        "hugo.petit@example.com",
        (
            DemoGoal(
                "Sailing trip",
                GoalType.OTHER,
                RiskProfile.BALANCED,
                15_000_00,
                3,
                1_000_00,
                250_00,
                history_months=9,
                quarterly_fee_cents=5_00,
            ),
        ),
    ),
    DemoClient(
        "Inès Moreau",
        "ines.moreau@example.com",
        (
            DemoGoal(
                "Retirement",
                GoalType.RETIREMENT,
                RiskProfile.MODERATE,
                150_000_00,
                15,
                30_000_00,
                600_00,
                deposit_every=6,
                quarterly_fee_cents=20_00,
            ),
        ),
    ),
)


def add_months(day: date, months: int) -> date:
    total = day.year * 12 + day.month - 1 + months
    return date(total // 12, total % 12 + 1, min(day.day, 28))


def get_or_create_client(session: Session, spec: DemoClient) -> User:
    user = session.scalars(select(User).where(User.email == spec.email)).first()
    if user is None:
        user = User(name=spec.name, email=spec.email)
        session.add(user)
        session.commit()
    return user


def get_or_create_goal(session: Session, owner: User, spec: DemoGoal, today: date) -> Goal:
    goal = session.scalars(
        select(Goal).where(Goal.user_id == owner.id, Goal.name == spec.name)
    ).first()
    if goal is None:
        goal = Goal(
            user_id=owner.id,
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
    """Replay past months: a deposit, a quarterly fee, the month's market movement and a
    rebalance check, in that order within each month."""
    this_month = today.replace(day=1)
    start = add_months(this_month, -spec.history_months)
    shock_month = add_months(this_month, -spec.shock_months_ago) if spec.shock_months_ago else None
    for i in range(spec.history_months):
        day = add_months(start, i)
        key = f"seed-{day:%Y-%m}"
        # A replayed month is complete: re-checking drift now would use today's holdings.
        if ledger.find_entry(session, f"mtm:{goal.id}:{day:%Y-%m}") is not None:
            continue
        if i % spec.deposit_every == 0:
            at = datetime(day.year, day.month, 1, 9, 0, tzinfo=UTC)
            amount = spec.initial_cents + spec.monthly_cents if i == 0 else spec.monthly_cents
            ledger.deposit(session, goal, amount, key, today=day, created_at=at)
        if spec.quarterly_fee_cents and day.month % 3 == 0:
            fee_at = datetime(day.year, day.month, 28, 16, 0, tzinfo=UTC)
            ledger.charge_fee(session, goal, spec.quarterly_fee_cents, key, created_at=fee_at)
        month_end = datetime(day.year, day.month, 28, 17, 0, tzinfo=UTC)
        returns = spec.shock if day == shock_month else None
        ledger.mark_to_market(
            session, goal, day.year, day.month, created_at=month_end, returns=returns
        )
        ledger.rebalance(session, goal, as_of=day.replace(day=28), created_at=month_end)


def seed_demo_goals(session: Session, today: date) -> list[Goal]:
    owner = demo_user(session)
    goals = []
    for spec in DEMO_GOALS:
        goal = get_or_create_goal(session, owner, spec, today)
        seed_goal_history(session, goal, spec, today)
        goals.append(goal)
    return goals


def seed_clients(session: Session, today: date) -> list[User]:
    # The demo user must exist first: the app acts for the first user.
    demo_user(session)
    session.commit()
    clients = []
    for spec in SUPPORT_CLIENTS:
        client = get_or_create_client(session, spec)
        for goal_spec in spec.goals:
            goal = get_or_create_goal(session, client, goal_spec, today)
            seed_goal_history(session, goal, goal_spec, today)
        clients.append(client)
    return clients


def seed(session: Session, today: date) -> list[Goal]:
    """Seed everything. Returns the demo user's goals."""
    goals = seed_demo_goals(session, today)
    seed_clients(session, today)
    return goals


def main() -> None:
    today = date.today()
    with get_sessionmaker()() as session:
        if "--if-empty" in sys.argv and session.scalars(select(Goal.id).limit(1)).first():
            print("Goals already exist; keeping the demo user's goals as they are.")
            goals = []
        else:
            goals = seed_demo_goals(session, today)
        clients = seed_clients(session, today)
        result = ledger.reconcile(session)
        print(
            f"Seeded {len(goals)} demo goals and {len(clients)} support clients. "
            f"Ledger reconciled: {result.ok}"
        )
        if not result.ok:
            raise SystemExit("Reconciliation failed after seeding.")


if __name__ == "__main__":
    main()
