from datetime import date

from fastapi.testclient import TestClient
from hypothesis import given
from hypothesis import strategies as st
from sqlalchemy.orm import Session

from cairn.domain.profiles import ASSET_CLASSES, PROFILES, AssetClass, RiskProfile
from cairn.domain.rebalancing import max_drift, rebalance_transfers
from cairn.domain.simulation import monthly_asset_returns
from cairn.services import ledger
from tests.factories import make_goal

BALANCED = PROFILES[RiskProfile.BALANCED].weights
holdings_strategy = st.lists(st.integers(0, 10**10), min_size=4, max_size=4).map(
    lambda values: dict(zip(ASSET_CLASSES, values, strict=True))
)
targets = st.sampled_from([PROFILES[p].weights for p in RiskProfile])


def test_no_transfers_within_threshold() -> None:
    # 4 points off on two classes: inside the 5-point band.
    holdings = {
        AssetClass.GLOBAL_EQUITY: 49_000,
        AssetClass.EMERGING_EQUITY: 10_000,
        AssetClass.EURO_GOV_BONDS: 31_000,
        AssetClass.MONEY_MARKET: 10_000,
    }
    assert rebalance_transfers(holdings, BALANCED) == {}


def test_transfers_when_drift_exceeds_threshold() -> None:
    holdings = {
        AssetClass.GLOBAL_EQUITY: 60_000,
        AssetClass.EMERGING_EQUITY: 10_000,
        AssetClass.EURO_GOV_BONDS: 20_000,
        AssetClass.MONEY_MARKET: 10_000,
    }
    transfers = rebalance_transfers(holdings, BALANCED)
    assert transfers == {AssetClass.GLOBAL_EQUITY: -15_000, AssetClass.EURO_GOV_BONDS: 15_000}


@given(holdings=holdings_strategy, target=targets)
def test_transfers_balance_and_restore_target(
    holdings: dict[AssetClass, int], target: dict[AssetClass, float]
) -> None:
    transfers = rebalance_transfers(holdings, target)
    assert sum(transfers.values()) == 0
    if not transfers:
        assert max_drift(holdings, target) <= 0.05
        return
    after = {a: holdings[a] + transfers.get(a, 0) for a in ASSET_CLASSES}
    total = sum(after.values())
    assert total == sum(holdings.values())
    for asset in ASSET_CLASSES:
        assert abs(after[asset] - total * target[asset]) <= 1  # within one cent of target
        assert after[asset] >= 0


def test_monthly_returns_are_deterministic() -> None:
    assert monthly_asset_returns(7, 100) == monthly_asset_returns(7, 100)
    assert monthly_asset_returns(7, 100) != monthly_asset_returns(7, 101)


def test_market_moves_then_rebalance_posts_one_entry(session: Session) -> None:
    goal = make_goal(session, profile="bold")
    ledger.deposit(session, goal, 1_000_000, "d", today=date(2026, 1, 1))
    as_of = date(2026, 1, 1)
    # Move prices month by month until the portfolio has drifted past the threshold.
    for i in range(240):
        ledger.mark_to_market(session, goal, 2026 + i // 12, i % 12 + 1)
        target = ledger.current_allocation(goal, as_of)
        if max_drift(ledger.holdings(session, goal), target) > 0.05:
            break
    else:
        raise AssertionError("prices never drifted enough")

    value_before = sum(ledger.holdings(session, goal).values())
    outcome = ledger.rebalance(session, goal, as_of)
    assert outcome.created and outcome.entry is not None
    assert sum(line.amount_cents for line in outcome.entry.lines) == 0
    assert sum(ledger.holdings(session, goal).values()) == value_before
    assert max_drift(ledger.holdings(session, goal), outcome.target) < 0.0001

    again = ledger.rebalance(session, goal, as_of)
    assert not again.created and again.entry is not None
    assert again.entry.id == outcome.entry.id
    assert ledger.reconcile(session).ok


def test_mark_to_market_is_idempotent_per_month(session: Session) -> None:
    goal = make_goal(session)
    ledger.deposit(session, goal, 500_000, "d", today=date(2026, 1, 1))
    first = ledger.mark_to_market(session, goal, 2026, 2)
    second = ledger.mark_to_market(session, goal, 2026, 2)
    assert first is not None and second is not None
    assert first.id == second.id
    assert ledger.reconcile(session).ok


def test_rebalance_endpoint(client: TestClient) -> None:
    goal = client.post(
        "/goals",
        json={
            "name": "Retirement",
            "type": "retirement",
            "target_cents": 50_000_000,
            "target_date": "2050-06-01",
            "monthly_contribution_cents": 40_000,
            "profile": "dynamic",
        },
    ).json()
    client.post(
        f"/goals/{goal['id']}/deposits",
        json={"amount_cents": 100_000},
        headers={"Idempotency-Key": "x"},
    )
    # Freshly invested at target: nothing to do.
    response = client.post(f"/goals/{goal['id']}/rebalance", json={"as_of": "2026-01-01"})
    assert response.status_code == 200
    body = response.json()
    assert body["rebalanced"] is False
    assert body["threshold"] == 0.05
    assert client.get(f"/goals/{goal['id']}/rebalances").json() == []
