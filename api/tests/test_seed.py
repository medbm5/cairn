import importlib.util
from datetime import date
from pathlib import Path
from types import ModuleType

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cairn.models import Goal, JournalEntry, User
from cairn.services import ledger


def load_seed() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "scripts" / "seed.py"
    spec = importlib.util.spec_from_file_location("seed_script", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_seed_builds_a_reconciled_history_and_is_safe_to_run_twice(session: Session) -> None:
    seed = load_seed()
    today = date(2026, 10, 24)
    seed.seed(session, today)
    entries = session.scalar(select(func.count(JournalEntry.id)))
    goals = session.scalar(select(func.count(Goal.id)))
    # Three goals for the demo user, six for the five support clients.
    assert goals == 9
    assert session.scalar(select(func.count(User.id))) == 6

    seed.seed(session, today)
    assert session.scalar(select(func.count(JournalEntry.id))) == entries
    assert session.scalar(select(func.count(Goal.id))) == 9
    assert session.scalar(select(func.count(User.id))) == 6

    result = ledger.reconcile(session)
    assert result.ok
    kinds = set(session.scalars(select(JournalEntry.kind)))
    assert kinds == {"deposit", "fee", "market", "rebalance"}
    # History is dated in the past, month by month.
    first = session.scalar(select(func.min(JournalEntry.created_at)))
    assert first is not None and (first.year, first.month) == (2024, 4)  # 30 months back


def test_seeded_goals_have_different_profiles_and_horizons(session: Session) -> None:
    seed = load_seed()
    goals = seed.seed(session, date(2026, 10, 24))
    assert len({g.profile for g in goals}) == 3
    assert len({g.target_date for g in goals}) == 3
    for goal in goals:
        assert sum(ledger.holdings(session, goal).values()) > 0
