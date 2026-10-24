"""Historical stress tests, replayed on a goal's allocation.

The scenarios are STYLISED APPROXIMATIONS of three market episodes, not historical data. Each is a
few phases; within a phase every month has the same return, chosen so the phase compounds to
the total shown. The totals are round figures in the spirit of what happened.
"""

from dataclasses import dataclass
from enum import StrEnum

from cairn.domain.money import split_cents
from cairn.domain.profiles import ASSET_CLASSES, AssetClass, Weights
from cairn.domain.rebalancing import rebalance_transfers


class Scenario(StrEnum):
    GFC_2008 = "gfc_2008"
    COVID_2020 = "covid_2020"
    RATES_2022 = "rates_2022"


@dataclass(frozen=True)
class Phase:
    months: int
    # Total simple return over the phase: global equity, emerging equity, gov bonds, money market.
    total_returns: tuple[float, float, float, float]


@dataclass(frozen=True)
class ScenarioInfo:
    name: str
    description: str
    phases: tuple[Phase, ...]

    @property
    def months(self) -> int:
        return sum(phase.months for phase in self.phases)


SCENARIOS: dict[Scenario, ScenarioInfo] = {
    # About 17 months of falling shares (late 2007 to early 2009) while government bonds rose,
    # then a long, partial recovery.
    Scenario.GFC_2008: ScenarioInfo(
        "Global financial crisis, 2008",
        "Shares fell for about 17 months; government bonds gained.",
        (
            Phase(17, (-0.55, -0.60, 0.10, 0.03)),
            Phase(43, (1.35, 1.40, 0.15, 0.02)),
        ),
    ),
    # One very sharp month in March 2020, then a fast rebound.
    Scenario.COVID_2020: ScenarioInfo(
        "Covid shock, 2020",
        "Shares dropped sharply in one month and recovered within months.",
        (
            Phase(1, (-0.13, -0.15, -0.01, 0.0)),
            Phase(5, (0.20, 0.22, 0.02, 0.0)),
            Phase(6, (0.08, 0.10, 0.01, 0.0)),
        ),
    ),
    # 2022: rising interest rates pushed shares and bonds down together, so bonds did not cushion.
    Scenario.RATES_2022: ScenarioInfo(
        "Rate shock, 2022",
        "Shares and bonds fell together as interest rates rose.",
        (
            Phase(10, (-0.20, -0.25, -0.17, 0.0)),
            Phase(14, (0.25, 0.12, 0.06, 0.04)),
        ),
    ),
}


def monthly_returns(scenario: Scenario) -> list[dict[AssetClass, float]]:
    """One dict of simple returns per month."""
    path = []
    for phase in SCENARIOS[scenario].phases:
        monthly = {
            asset: (1 + total) ** (1 / phase.months) - 1
            for asset, total in zip(ASSET_CLASSES, phase.total_returns, strict=True)
        }
        path.extend([monthly] * phase.months)
    return path


@dataclass(frozen=True)
class Replay:
    values: list[int]  # portfolio value in cents at the start and after each month
    max_drawdown: float  # largest fall from a peak, as a fraction (0.3 = -30%)
    months_to_recover: int | None  # months from the lowest point back to the prior peak
    rebalances: int


def drawdown_stats(values: list[int]) -> tuple[float, int | None]:
    peak = values[0]
    worst, worst_peak, worst_at = 0.0, values[0], 0
    for t, value in enumerate(values):
        peak = max(peak, value)
        drawdown = 1 - value / peak if peak else 0.0
        if drawdown > worst:
            worst, worst_peak, worst_at = drawdown, peak, t
    if worst == 0:
        return 0.0, 0
    for t in range(worst_at, len(values)):
        if values[t] >= worst_peak:
            return worst, t - worst_at
    return worst, None


def replay(scenario: Scenario, weights: Weights, start_cents: int, rebalance: bool) -> Replay:
    """Replay a scenario on a portfolio invested at `weights`, optionally with drift rebalancing."""
    holdings = split_cents(start_cents, weights, ASSET_CLASSES)
    values = [start_cents]
    rebalances = 0
    for returns in monthly_returns(scenario):
        holdings = {a: round(cents * (1 + returns[a])) for a, cents in holdings.items()}
        if rebalance:
            transfers = rebalance_transfers(holdings, weights)
            if transfers:
                rebalances += 1
                holdings = {a: holdings[a] + transfers.get(a, 0) for a in ASSET_CLASSES}
        values.append(sum(holdings.values()))
    max_drawdown, months_to_recover = drawdown_stats(values)
    return Replay(values, max_drawdown, months_to_recover, rebalances)
