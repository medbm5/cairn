import pytest
from fastapi.testclient import TestClient

from cairn.domain.profiles import AssetClass
from cairn.domain.stress import SCENARIOS, Scenario, drawdown_stats, monthly_returns, replay

ALL_EQUITY = {
    AssetClass.GLOBAL_EQUITY: 1.0,
    AssetClass.EMERGING_EQUITY: 0.0,
    AssetClass.EURO_GOV_BONDS: 0.0,
    AssetClass.MONEY_MARKET: 0.0,
}
NO_EQUITY = {
    AssetClass.GLOBAL_EQUITY: 0.0,
    AssetClass.EMERGING_EQUITY: 0.0,
    AssetClass.EURO_GOV_BONDS: 0.6,
    AssetClass.MONEY_MARKET: 0.4,
}


@pytest.mark.parametrize(
    ("scenario", "months"),
    [(Scenario.GFC_2008, 60), (Scenario.COVID_2020, 12), (Scenario.RATES_2022, 24)],
)
def test_scenario_paths_have_documented_length(scenario: Scenario, months: int) -> None:
    assert SCENARIOS[scenario].months == months
    assert len(monthly_returns(scenario)) == months
    assert len(replay(scenario, ALL_EQUITY, 100_000, rebalance=False).values) == months + 1


def test_phases_compound_to_their_totals() -> None:
    path = monthly_returns(Scenario.GFC_2008)[:17]
    growth = 1.0
    for month in path:
        growth *= 1 + month[AssetClass.GLOBAL_EQUITY]
    assert growth == pytest.approx(0.45)


def test_no_equity_has_smaller_drawdown_than_full_equity_in_2008() -> None:
    equity = replay(Scenario.GFC_2008, ALL_EQUITY, 1_000_000, rebalance=False)
    safe = replay(Scenario.GFC_2008, NO_EQUITY, 1_000_000, rebalance=False)
    assert safe.max_drawdown < equity.max_drawdown
    assert equity.max_drawdown == pytest.approx(0.55, abs=0.001)


def test_bonds_do_not_cushion_in_2022() -> None:
    safe = replay(Scenario.RATES_2022, NO_EQUITY, 1_000_000, rebalance=False)
    assert safe.max_drawdown > 0.05


def test_drawdown_stats() -> None:
    assert drawdown_stats([100, 120, 60, 90, 120, 130]) == (0.5, 2)
    assert drawdown_stats([100, 80, 90]) == (pytest.approx(0.2), None)
    assert drawdown_stats([100, 110, 120]) == (0.0, 0)


def test_stress_test_endpoint(client: TestClient) -> None:
    goal = client.post(
        "/goals",
        json={
            "name": "Retirement",
            "type": "retirement",
            "target_cents": 50_000_000,
            "target_date": "2050-06-01",
            "monthly_contribution_cents": 40_000,
            "profile": "balanced",
        },
    ).json()
    response = client.post(f"/goals/{goal['id']}/stress-tests/gfc_2008")
    assert response.status_code == 200
    body = response.json()
    assert body["months"] == 60
    assert len(body["with_rebalancing"]["values"]) == 61
    assert body["without_rebalancing"]["max_drawdown"] > 0
    assert body["with_rebalancing"]["rebalances"] >= 1
    assert client.post(f"/goals/{goal['id']}/stress-tests/dotcom_2000").status_code == 422
