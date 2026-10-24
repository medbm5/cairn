"""Helpers to create test data directly through the ORM."""

from datetime import date

from sqlalchemy.orm import Session

from cairn.models import Goal
from cairn.services.goals import demo_user


def make_goal(session: Session, profile: str = "balanced") -> Goal:
    goal = Goal(
        user_id=demo_user(session).id,
        name="Test goal",
        type="other",
        target_cents=10_000_000,
        target_date=date(2040, 1, 1),
        monthly_contribution_cents=10_000,
        profile=profile,
    )
    session.add(goal)
    session.commit()
    return goal
