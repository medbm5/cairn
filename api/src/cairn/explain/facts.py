"""Typed facts per topic: the only numbers an explanation may use.

The UI sends facts it received from the engine's endpoints; the builders below make the same
objects from engine outputs on the server side (used by tests and the seed script).
"""

from datetime import date
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

from cairn.domain.glide_path import PRESERVATION_MIX
from cairn.domain.profiles import PROFILES, AssetClass, RiskProfile, equity_share
from cairn.domain.simulation import SimulationResult
from cairn.domain.solver import GoalInputs, Lever, Solution
from cairn.domain.stress import Replay, Scenario

Fraction = float  # 0.25 means 25%


class Topic(StrEnum):
    PROJECTION = "projection"
    ALLOCATION = "allocation"
    GLIDE_PATH = "glide_path"
    REBALANCE = "rebalance"
    STRESS_TEST = "stress_test"
    LEDGER_ENTRY = "ledger_entry"
    SUPPORT_ANSWER = "support_answer"
    SOLVER = "solver"
    TERM = "term"


class ProjectionFacts(BaseModel):
    profile: RiskProfile
    target_cents: int = Field(ge=0)
    horizon_months: int = Field(ge=1, le=600)
    monthly_contribution_cents: int = Field(ge=0)
    p10_cents: int = Field(ge=0)
    p50_cents: int = Field(ge=0)
    p90_cents: int = Field(ge=0)
    success_probability: Fraction = Field(ge=0, le=1)


class AllocationFacts(BaseModel):
    profile: RiskProfile
    weights: dict[AssetClass, Fraction]


class GlidePathFacts(BaseModel):
    profile: RiskProfile
    years_remaining: int = Field(ge=0, le=50)
    equity_share_now: Fraction = Field(ge=0, le=1)
    equity_share_at_goal: Fraction = Field(ge=0, le=1)


class RebalanceFacts(BaseModel):
    # Not stored with past rebalances, so optional; the template words it without a figure.
    largest_drift: Fraction | None = Field(default=None, ge=0, le=1)
    threshold: Fraction = Field(ge=0, le=1)
    moved_cents: int = Field(ge=0)


class StressTestFacts(BaseModel):
    scenario: Scenario
    start_cents: int = Field(ge=0)
    max_drawdown: Fraction = Field(ge=0, le=1)
    max_drawdown_rebalanced: Fraction = Field(ge=0, le=1)
    months_to_recover: int | None = Field(default=None, ge=0)


class LedgerEntryFacts(BaseModel):
    kind: str = Field(max_length=20)
    amount_cents: int = Field(ge=0)
    accounts: list[str] = Field(max_length=10)


class SupportAnswerFacts(BaseModel):
    """A support question about one client, answered from their timeline only.

    `month_change` breaks the balance change of one month into its parts; the parts are computed
    in code and must add up to the change exactly, to the cent. Amounts are signed: a negative
    change or market effect is a loss. `last_rebalance` describes the client's latest rebalance.
    """

    question: str = Field(max_length=300)
    focus: Literal["month_change", "last_rebalance"]
    year: int = Field(ge=2000, le=2100)
    month: int = Field(ge=1, le=12)
    start_balance_cents: int = Field(ge=0)
    end_balance_cents: int = Field(ge=0)
    change_cents: int
    market_effect_cents: int
    deposits_cents: int = Field(ge=0)
    fees_cents: int = Field(ge=0)
    market_by_asset_cents: dict[AssetClass, int]
    rebalanced_this_month: bool
    last_rebalance_year: int | None = Field(default=None, ge=2000, le=2100)
    last_rebalance_month: int | None = Field(default=None, ge=1, le=12)
    last_rebalance_day: int | None = Field(default=None, ge=1, le=31)
    last_rebalance_moved_cents: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def check_parts_add_up(self) -> Self:
        if self.change_cents != self.end_balance_cents - self.start_balance_cents:
            raise ValueError("change_cents must equal end minus start balance.")
        parts = self.market_effect_cents + self.deposits_cents - self.fees_cents
        if parts != self.change_cents:
            raise ValueError("Market effect, deposits and fees must add up to the change.")
        if sum(self.market_by_asset_cents.values()) != self.market_effect_cents:
            raise ValueError("The market effect per asset class must add up to the total.")
        return self


class SolverFacts(BaseModel):
    """The goal solver's three options, each changing one thing on its own.

    `needed_monthly_contribution_cents` and `needed_horizon_months` are what it takes to reach
    `target_probability`; `reachable_target_cents` is the largest target it reaches unchanged.
    A lever that is out of reach (no amount, or no date within 40 years) is not feasible.
    """

    target_cents: int = Field(ge=0)
    monthly_contribution_cents: int = Field(ge=0)
    horizon_months: int = Field(ge=1, le=600)
    current_probability: Fraction = Field(ge=0, le=1)
    target_probability: Fraction = Field(ge=0.5, le=0.95)
    needed_monthly_contribution_cents: int = Field(ge=0)
    contribution_increase_cents: int
    contribution_feasible: bool
    probability_with_contribution: Fraction = Field(ge=0, le=1)
    needed_horizon_months: int = Field(ge=1, le=600)
    horizon_extension_months: int
    needed_goal_year: int = Field(ge=2000, le=2100)
    needed_goal_month: int = Field(ge=1, le=12)
    horizon_feasible: bool
    probability_with_horizon: Fraction = Field(ge=0, le=1)
    reachable_target_cents: int = Field(ge=0)
    target_reduction_cents: int
    target_feasible: bool
    probability_with_target: Fraction = Field(ge=0, le=1)

    @model_validator(mode="after")
    def check_differences(self) -> Self:
        if (
            self.contribution_increase_cents
            != self.needed_monthly_contribution_cents - self.monthly_contribution_cents
            or self.horizon_extension_months != self.needed_horizon_months - self.horizon_months
            or self.target_reduction_cents != self.target_cents - self.reachable_target_cents
        ):
            raise ValueError("Each change must equal the new value minus the current one.")
        return self


FactsModel = (
    ProjectionFacts
    | AllocationFacts
    | GlidePathFacts
    | RebalanceFacts
    | StressTestFacts
    | LedgerEntryFacts
    | SupportAnswerFacts
    | SolverFacts
)

FACT_MODELS: dict[Topic, type[FactsModel]] = {
    Topic.PROJECTION: ProjectionFacts,
    Topic.ALLOCATION: AllocationFacts,
    Topic.GLIDE_PATH: GlidePathFacts,
    Topic.REBALANCE: RebalanceFacts,
    Topic.STRESS_TEST: StressTestFacts,
    Topic.LEDGER_ENTRY: LedgerEntryFacts,
    Topic.SUPPORT_ANSWER: SupportAnswerFacts,
    Topic.SOLVER: SolverFacts,
}


# --- Builders from engine outputs ---


def projection_facts(
    result: SimulationResult,
    *,
    profile: RiskProfile,
    target_cents: int,
    monthly_contribution_cents: int,
) -> ProjectionFacts:
    return ProjectionFacts(
        profile=profile,
        target_cents=target_cents,
        horizon_months=result.months[-1],
        monthly_contribution_cents=monthly_contribution_cents,
        p10_cents=result.percentiles[10][-1],
        p50_cents=result.percentiles[50][-1],
        p90_cents=result.percentiles[90][-1],
        success_probability=result.success_probability or 0.0,
    )


def allocation_facts(profile: RiskProfile) -> AllocationFacts:
    return AllocationFacts(profile=profile, weights=PROFILES[profile].weights)


def glide_path_facts(
    profile: RiskProfile, years_remaining: int, now: dict[AssetClass, float]
) -> GlidePathFacts:
    return GlidePathFacts(
        profile=profile,
        years_remaining=years_remaining,
        equity_share_now=equity_share(now),
        equity_share_at_goal=equity_share(PRESERVATION_MIX),
    )


def stress_test_facts(
    scenario: Scenario, start_cents: int, plain: Replay, rebalanced: Replay
) -> StressTestFacts:
    return StressTestFacts(
        scenario=scenario,
        start_cents=start_cents,
        max_drawdown=plain.max_drawdown,
        max_drawdown_rebalanced=rebalanced.max_drawdown,
        months_to_recover=plain.months_to_recover,
    )


def solver_facts(solution: Solution, inputs: GoalInputs, goal_date: date) -> SolverFacts:
    """`goal_date` is the date the horizon option gives (today plus its months)."""
    by_lever = {option.lever: option for option in solution.options}
    contribution = by_lever[Lever.CONTRIBUTION]
    horizon = by_lever[Lever.HORIZON]
    target = by_lever[Lever.TARGET]
    return SolverFacts(
        target_cents=inputs.target_cents,
        monthly_contribution_cents=inputs.monthly_contribution_cents,
        horizon_months=inputs.horizon_months,
        current_probability=solution.current_probability,
        target_probability=solution.target_probability,
        needed_monthly_contribution_cents=contribution.value,
        contribution_increase_cents=contribution.delta,
        contribution_feasible=contribution.feasible,
        probability_with_contribution=contribution.success_probability,
        needed_horizon_months=horizon.value,
        horizon_extension_months=horizon.delta,
        needed_goal_year=goal_date.year,
        needed_goal_month=goal_date.month,
        horizon_feasible=horizon.feasible,
        probability_with_horizon=horizon.success_probability,
        reachable_target_cents=target.value,
        target_reduction_cents=-target.delta,
        target_feasible=target.feasible,
        probability_with_target=target.success_probability,
    )
