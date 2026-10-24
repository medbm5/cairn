"""Horizon-based glide path: the portfolio becomes safer as the goal date approaches.

With 10 years or more to go, the profile's own allocation applies. Over the last 10 years the
weights move linearly toward a capital-preservation mix, which is reached at the goal date.
"""

from functools import partial

from cairn.domain.profiles import PROFILES, AssetClass, RiskProfile, Weights

GLIDE_MONTHS = 120

PRESERVATION_MIX: Weights = {
    AssetClass.GLOBAL_EQUITY: 0.10,
    AssetClass.EMERGING_EQUITY: 0.00,
    AssetClass.EURO_GOV_BONDS: 0.40,
    AssetClass.MONEY_MARKET: 0.50,
}


def allocation_at(profile: RiskProfile, months_remaining: int) -> Weights:
    start = PROFILES[profile].weights
    progress = min(max(months_remaining, 0), GLIDE_MONTHS) / GLIDE_MONTHS  # 1 = far, 0 = at goal
    return {
        asset: progress * start[asset] + (1 - progress) * PRESERVATION_MIX[asset] for asset in start
    }


def glide_path_for(profile: RiskProfile) -> partial[Weights]:
    """The glide path as an allocation function of months remaining, for the simulation."""
    return partial(allocation_at, profile)


def yearly_allocations(profile: RiskProfile, horizon_months: int) -> list[tuple[int, int, Weights]]:
    """(year, months_remaining, weights) from today (year 0) to the goal date."""
    years = -(-horizon_months // 12)  # ceiling division
    rows = []
    for year in range(years + 1):
        remaining = max(horizon_months - year * 12, 0)
        rows.append((year, remaining, allocation_at(profile, remaining)))
    return rows
