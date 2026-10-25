"""Goal solver: which single change would reach a chosen chance of success?

Three levers, each moved on its own: the monthly contribution, the horizon and the target. Every
answer comes from the glide-path simulation with a fixed seed and fewer paths, so the same goal
always gives the same answer, and quickly.

With the random draws fixed, a path's final value is `initial * A + contribution * B`, where A
and B depend only on the draws. So the chance of success can only rise with the contribution and
only fall with the target, and the boundary found is exact. The horizon also changes the glide
path, so its chance is only roughly monotonic; bisection still returns a horizon that reaches the
target probability, though a slightly shorter one may exist.
"""

import math
from dataclasses import dataclass
from enum import StrEnum

import numpy as np

from cairn.domain.glide_path import glide_path_for
from cairn.domain.profiles import RiskProfile
from cairn.domain.simulation import FloatArray, growth_factors

SOLVER_SEED = 2_026
SOLVER_PATHS = 2_000
DEFAULT_TARGET_PROBABILITY = 0.8
MIN_HORIZON_MONTHS = 12
MAX_HORIZON_MONTHS = 480  # 40 years
# A chance is a count of paths divided by the path count; this absorbs float noise in `p * n`.
EPSILON = 1e-9


class Lever(StrEnum):
    CONTRIBUTION = "contribution"
    HORIZON = "horizon"
    TARGET = "target"


@dataclass(frozen=True)
class GoalInputs:
    initial_cents: int
    monthly_contribution_cents: int
    horizon_months: int
    target_cents: int
    profile: RiskProfile


@dataclass(frozen=True)
class Grid:
    """The steps answers snap to, and the largest monthly contribution worth considering."""

    contribution_cents: int = 100  # whole euros
    horizon_months: int = 1
    target_cents: int = 100_00  # rounded down to 100 euros
    max_contribution_cents: int = 1_000_000_00


DEFAULT_GRID = Grid()


@dataclass(frozen=True)
class Option:
    lever: Lever
    value: int  # cents, or months for the horizon
    current: int
    success_probability: float
    feasible: bool  # false when even the cap does not reach the target probability

    @property
    def delta(self) -> int:
        return self.value - self.current

    @property
    def relative_change(self) -> float:
        # From nothing, any change is large: dividing by one cent or month keeps it finite.
        return abs(self.delta) / max(abs(self.current), 1)


@dataclass(frozen=True)
class Solution:
    target_probability: float
    current_probability: float
    options: list[Option]  # feasible first, then the smallest relative change


def final_value_factors(
    profile: RiskProfile, horizon_months: int, *, paths: int, seed: int
) -> tuple[FloatArray, FloatArray]:
    """(A, B) per path, so that the final value is `initial * A + contribution * B`."""
    growth = growth_factors(
        horizon_months=horizon_months,
        allocation=glide_path_for(profile),
        paths=paths,
        seed=seed,
    )
    a = np.ones(paths)
    b = np.zeros(paths)
    for row in growth:  # the same recursion as the simulation: value * growth + contribution
        a = a * row
        b = b * row + 1.0
    return a, b


def _chance(a: FloatArray, b: FloatArray, initial: int, monthly: int, target: int) -> float:
    return float(np.mean(initial * a + monthly * b >= target))


def _reaches(chance: float, target_probability: float) -> bool:
    return chance >= target_probability - EPSILON


def success_probability(
    inputs: GoalInputs, *, paths: int = SOLVER_PATHS, seed: int = SOLVER_SEED
) -> float:
    """The chance of reaching the target, measured the way the solver measures it."""
    a, b = final_value_factors(inputs.profile, inputs.horizon_months, paths=paths, seed=seed)
    return _chance(
        a, b, inputs.initial_cents, inputs.monthly_contribution_cents, inputs.target_cents
    )


def solve_monthly_contribution(
    inputs: GoalInputs,
    target_probability: float = DEFAULT_TARGET_PROBABILITY,
    *,
    grid: Grid = DEFAULT_GRID,
    paths: int = SOLVER_PATHS,
    seed: int = SOLVER_SEED,
) -> Option:
    """The smallest monthly contribution (on the grid) reaching the target probability."""
    a, b = final_value_factors(inputs.profile, inputs.horizon_months, paths=paths, seed=seed)
    step = grid.contribution_cents

    def chance_at(steps: int) -> float:
        return _chance(a, b, inputs.initial_cents, steps * step, inputs.target_cents)

    def option(steps: int, feasible: bool) -> Option:
        return Option(
            Lever.CONTRIBUTION,
            steps * step,
            inputs.monthly_contribution_cents,
            chance_at(steps),
            feasible,
        )

    high = grid.max_contribution_cents // step
    if not _reaches(chance_at(high), target_probability):
        return option(high, feasible=False)
    if _reaches(chance_at(0), target_probability):
        return option(0, feasible=True)
    low = 0  # invariant: `low` falls short, `high` reaches
    while high - low > 1:
        middle = (low + high) // 2
        if _reaches(chance_at(middle), target_probability):
            high = middle
        else:
            low = middle
    return option(high, feasible=True)


def solve_horizon(
    inputs: GoalInputs,
    target_probability: float = DEFAULT_TARGET_PROBABILITY,
    *,
    grid: Grid = DEFAULT_GRID,
    paths: int = SOLVER_PATHS,
    seed: int = SOLVER_SEED,
) -> Option:
    """The shortest horizon (on the grid, at most 40 years) reaching the target probability,
    with the contribution unchanged."""
    step = grid.horizon_months

    def chance_at(steps: int) -> float:
        months = steps * step
        a, b = final_value_factors(inputs.profile, months, paths=paths, seed=seed)
        return _chance(
            a, b, inputs.initial_cents, inputs.monthly_contribution_cents, inputs.target_cents
        )

    def option(steps: int, chance: float, feasible: bool) -> Option:
        return Option(Lever.HORIZON, steps * step, inputs.horizon_months, chance, feasible)

    low = math.ceil(MIN_HORIZON_MONTHS / step)
    high = MAX_HORIZON_MONTHS // step
    at_high = chance_at(high)
    if not _reaches(at_high, target_probability):
        return option(high, at_high, feasible=False)
    at_low = chance_at(low)
    if _reaches(at_low, target_probability):
        return option(low, at_low, feasible=True)
    while high - low > 1:  # invariant: `low` falls short, `high` reaches
        middle = (low + high) // 2
        at_middle = chance_at(middle)
        if _reaches(at_middle, target_probability):
            high, at_high = middle, at_middle
        else:
            low = middle
    return option(high, at_high, feasible=True)


def solve_target(
    inputs: GoalInputs,
    target_probability: float = DEFAULT_TARGET_PROBABILITY,
    *,
    grid: Grid = DEFAULT_GRID,
    paths: int = SOLVER_PATHS,
    seed: int = SOLVER_SEED,
) -> Option:
    """The largest target (rounded down to the grid) reachable with the current contribution and
    horizon. Read straight off the sorted final values: no search needed."""
    a, b = final_value_factors(inputs.profile, inputs.horizon_months, paths=paths, seed=seed)
    finals = np.sort(inputs.initial_cents * a + inputs.monthly_contribution_cents * b)[::-1]
    # At least `needed` paths must end at or above the target.
    needed = max(math.ceil(target_probability * paths - EPSILON), 1)
    step = grid.target_cents
    target = int(finals[needed - 1] // step) * step
    chance = _chance(a, b, inputs.initial_cents, inputs.monthly_contribution_cents, target)
    return Option(Lever.TARGET, target, inputs.target_cents, chance, feasible=target >= step)


def solve(
    inputs: GoalInputs,
    target_probability: float = DEFAULT_TARGET_PROBABILITY,
    *,
    grid: Grid = DEFAULT_GRID,
    paths: int = SOLVER_PATHS,
    seed: int = SOLVER_SEED,
) -> Solution:
    """All three levers, the smallest change first."""
    options = [
        lever(inputs, target_probability, grid=grid, paths=paths, seed=seed)
        for lever in (solve_monthly_contribution, solve_horizon, solve_target)
    ]
    options.sort(key=lambda o: (not o.feasible, o.relative_change))
    return Solution(
        target_probability=target_probability,
        current_probability=success_probability(inputs, paths=paths, seed=seed),
        options=options,
    )
