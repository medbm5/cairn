from datetime import date

import pytest
from fastapi.testclient import TestClient
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy.orm import Session

from cairn.domain.money import split_cents
from cairn.domain.profiles import ASSET_CLASSES
from cairn.models import Goal
from cairn.services import ledger
from cairn.services.goals import demo_user

TODAY = date(2026, 1, 1)


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


# --- split_cents ---


@given(
    total=st.integers(-(10**12), 10**12),
    weights=st.lists(st.floats(0, 1), min_size=4, max_size=4).filter(lambda w: sum(w) > 0),
)
def test_split_cents_sums_exactly(total: int, weights: list[float]) -> None:
    keyed = dict(zip(ASSET_CLASSES, weights, strict=True))
    parts = split_cents(total, keyed, ASSET_CLASSES)
    assert sum(parts.values()) == total


def test_split_cents_follows_weights() -> None:
    parts = split_cents(100, {"a": 0.5, "b": 0.25, "c": 0.25}, ["a", "b", "c"])
    assert parts == {"a": 50, "b": 25, "c": 25}
    assert split_cents(1, {"a": 0.5, "b": 0.5}, ["a", "b"]) == {"a": 1, "b": 0}


# --- post_entry ---


def test_unbalanced_entry_is_rejected(session: Session) -> None:
    goal = make_goal(session)
    with pytest.raises(ledger.UnbalancedEntryError):
        ledger.post_entry(
            session,
            goal=goal,
            kind="test",
            idempotency_key="k1",
            description="broken",
            lines=[(ledger.EXTERNAL_BANK, -100), (ledger.CASH, 99)],
        )
    assert ledger.reconcile(session).entries_checked == 0


def test_deposit_invests_by_current_allocation(session: Session) -> None:
    goal = make_goal(session, profile="bold")
    entry, created = ledger.deposit(session, goal, 100_000, "first", today=TODAY)
    assert created
    assert sum(line.amount_cents for line in entry.lines) == 0
    holdings = ledger.holdings(session, goal)
    assert sum(holdings.values()) == 100_000
    assert ledger.contributed_cents(session, goal) == 100_000
    # 14 years out, a bold goal is fully on its profile: 75% global equity.
    assert holdings[ASSET_CLASSES[0]] == 75_000


def test_same_deposit_twice_creates_one_entry(session: Session) -> None:
    goal = make_goal(session)
    first, created_first = ledger.deposit(session, goal, 5_000, "same-key", today=TODAY)
    second, created_second = ledger.deposit(session, goal, 5_000, "same-key", today=TODAY)
    assert created_first and not created_second
    assert first.id == second.id
    assert len(ledger.entries(session, goal)) == 1
    assert ledger.contributed_cents(session, goal) == 5_000


def test_fee_larger_than_holdings_is_rejected(session: Session) -> None:
    goal = make_goal(session)
    ledger.deposit(session, goal, 1_000, "d", today=TODAY)
    with pytest.raises(ledger.InsufficientFundsError):
        ledger.charge_fee(session, goal, 1_001, "f")


operations = st.lists(
    st.one_of(
        st.tuples(st.just("deposit"), st.integers(1, 10_000_000)),
        st.tuples(st.just("fee"), st.integers(1, 50_000)),
    ),
    min_size=1,
    max_size=12,
)


@settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@given(ops=operations, profile=st.sampled_from(["prudent", "balanced", "bold"]))
def test_random_deposits_and_fees_always_reconcile(
    session: Session, ops: list[tuple[str, int]], profile: str
) -> None:
    goal = make_goal(session, profile)
    deposited = fees = 0
    for i, (kind, amount) in enumerate(ops):
        if kind == "deposit":
            ledger.deposit(session, goal, amount, f"op-{i}", today=TODAY)
            deposited += amount
        else:
            try:
                ledger.charge_fee(session, goal, amount, f"op-{i}")
                fees += amount
            except ledger.InsufficientFundsError:
                pass
        result = ledger.reconcile(session)
        assert result.ok, result
        assert result.total_cents == 0
    assert sum(ledger.holdings(session, goal).values()) == deposited - fees
    assert ledger.account_balances(session, goal).get(ledger.FEES, 0) == fees


# --- HTTP ---


def create_goal(client: TestClient) -> int:
    body = {
        "name": "Safety net",
        "type": "safety_net",
        "target_cents": 1_000_000,
        "target_date": date.today().replace(year=date.today().year + 3, day=1).isoformat(),
        "monthly_contribution_cents": 20_000,
        "profile": "prudent",
    }
    goal_id: int = client.post("/goals", json=body).json()["id"]
    return goal_id


def test_deposit_endpoint_is_idempotent(client: TestClient) -> None:
    goal_id = create_goal(client)
    headers = {"Idempotency-Key": "abc"}
    first = client.post(
        f"/goals/{goal_id}/deposits", json={"amount_cents": 25_000}, headers=headers
    )
    again = client.post(
        f"/goals/{goal_id}/deposits", json={"amount_cents": 25_000}, headers=headers
    )
    assert first.status_code == 201
    assert again.status_code == 200
    assert again.headers["Idempotent-Replayed"] == "true"
    assert first.json()["id"] == again.json()["id"]

    entries = client.get(f"/goals/{goal_id}/entries").json()
    assert len(entries) == 1
    assert entries[0]["lines"][0] == {"account": "external_bank", "amount_cents": -25_000}

    balance = client.get(f"/goals/{goal_id}/balance").json()
    assert balance["total_cents"] == 25_000
    assert balance["contributed_cents"] == 25_000

    reconciliation = client.get("/ledger/reconciliation").json()
    assert reconciliation["ok"] is True
    assert reconciliation["entries_checked"] == 1


def test_deposit_requires_idempotency_key(client: TestClient) -> None:
    goal_id = create_goal(client)
    response = client.post(f"/goals/{goal_id}/deposits", json={"amount_cents": 100})
    assert response.status_code == 422


def test_projection_starts_from_balance(client: TestClient) -> None:
    goal_id = create_goal(client)
    client.post(
        f"/goals/{goal_id}/deposits",
        json={"amount_cents": 80_000},
        headers={"Idempotency-Key": "1"},
    )
    projection = client.get(f"/goals/{goal_id}/projection", params={"paths": 200}).json()
    assert projection["start_cents"] == 80_000
    assert projection["simulation"]["p50"][0] == 80_000


def test_deleting_a_goal_keeps_the_ledger_reconciled(client: TestClient) -> None:
    kept, removed = create_goal(client), create_goal(client)
    for goal_id in (kept, removed):
        client.post(
            f"/goals/{goal_id}/deposits",
            json={"amount_cents": 10_000},
            headers={"Idempotency-Key": "k"},
        )
    assert client.delete(f"/goals/{removed}").status_code == 204
    reconciliation = client.get("/ledger/reconciliation").json()
    assert reconciliation["ok"] is True
    assert reconciliation["entries_checked"] == 1
