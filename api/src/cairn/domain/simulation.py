"""Vectorised Monte Carlo projection of a goal, in monthly steps.

Model: asset log returns are multivariate normal, built from the annual assumptions and the
correlation matrix in `profiles`. The portfolio is rebalanced to its target weights every month,
so its monthly log return is drawn from N(w . mu, w' Sigma w), with the weights allowed to change
month by month (the glide path). Contributions are added at the end of each month.

Inputs and outputs are integer cents; floats are used only inside this module.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from cairn.domain.profiles import (
    ASSET_CLASSES,
    ASSUMPTIONS,
    CORRELATIONS,
    AssetAssumption,
    AssetClass,
    Weights,
)

PERCENTILES: tuple[int, ...] = (10, 25, 50, 75, 90)
DEFAULT_PATHS = 5_000

FloatArray = npt.NDArray[np.float64]
# Either fixed weights, or a function of months remaining until the goal (a glide path).
Allocation = Weights | Callable[[int], Weights]


@dataclass(frozen=True)
class SimulationResult:
    seed: int
    months: list[int]
    percentiles: dict[int, list[int]]  # percentile -> value in cents, one per month (incl. month 0)
    contributed: list[int]  # total contributed in cents, one per month
    success_probability: float | None  # share of paths ending at or above the target


def monthly_log_moments(
    assumptions: Mapping[AssetClass, AssetAssumption] = ASSUMPTIONS,
) -> tuple[FloatArray, FloatArray]:
    """Monthly mean vector and covariance matrix of asset log returns."""
    annual_return = np.array([assumptions[a].expected_return for a in ASSET_CLASSES])
    annual_vol = np.array([assumptions[a].volatility for a in ASSET_CLASSES])
    # Convert an arithmetic annual return to the mean of a lognormal annual log return.
    annual_log_mean = np.log1p(annual_return) - annual_vol**2 / 2
    corr = np.array(CORRELATIONS)
    monthly_cov = np.outer(annual_vol, annual_vol) * corr / 12
    return annual_log_mean / 12, monthly_cov


def weights_by_month(allocation: Allocation, horizon_months: int) -> FloatArray:
    """Weight matrix of shape (horizon_months, n_assets); row t applies during month t+1."""
    if callable(allocation):
        rows = [allocation(horizon_months - t) for t in range(horizon_months)]
    else:
        rows = [allocation] * horizon_months
    return np.array([[row[a] for a in ASSET_CLASSES] for row in rows])


def simulate(
    *,
    initial_cents: int,
    monthly_contribution_cents: int,
    horizon_months: int,
    allocation: Allocation,
    target_cents: int | None = None,
    paths: int = DEFAULT_PATHS,
    seed: int | None = None,
    assumptions: Mapping[AssetClass, AssetAssumption] = ASSUMPTIONS,
) -> SimulationResult:
    if seed is None:
        seed = int(np.random.SeedSequence().generate_state(1)[0])
    rng = np.random.default_rng(seed)

    mu, cov = monthly_log_moments(assumptions)
    weights = weights_by_month(allocation, horizon_months)
    port_mean = weights @ mu  # (months,)
    port_std = np.sqrt(np.einsum("ti,ij,tj->t", weights, cov, weights))  # (months,)

    shocks = rng.standard_normal((horizon_months, paths))
    growth = np.exp(port_mean[:, None] + port_std[:, None] * shocks)  # (months, paths)

    values = np.empty((horizon_months + 1, paths))
    values[0] = initial_cents
    contribution = float(monthly_contribution_cents)
    for t in range(horizon_months):
        values[t + 1] = values[t] * growth[t] + contribution

    bands = np.percentile(values, PERCENTILES, axis=1)  # (len(PERCENTILES), months + 1)
    months = list(range(horizon_months + 1))
    success = None
    if target_cents is not None:
        success = float(np.mean(values[-1] >= target_cents))

    return SimulationResult(
        seed=seed,
        months=months,
        percentiles={
            p: np.rint(band).astype(np.int64).tolist()
            for p, band in zip(PERCENTILES, bands, strict=True)
        },
        contributed=[initial_cents + monthly_contribution_cents * m for m in months],
        success_probability=success,
    )


def monthly_asset_returns(
    seed: int, month: int, assumptions: Mapping[AssetClass, AssetAssumption] = ASSUMPTIONS
) -> dict[AssetClass, float]:
    """Deterministic simple returns of each asset class for one month, used for the demo's price
    movements. The same (seed, month) always gives the same returns."""
    mu, cov = monthly_log_moments(assumptions)
    rng = np.random.default_rng([seed, month])
    log_returns = rng.multivariate_normal(mu, cov)
    return {asset: float(np.expm1(r)) for asset, r in zip(ASSET_CLASSES, log_returns, strict=True)}
