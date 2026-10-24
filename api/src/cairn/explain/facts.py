"""Typed facts per topic: the only numbers an explanation may use.

The UI sends facts it received from the engine's endpoints; the builders below make the same
objects from engine outputs on the server side (used by tests and the seed script).
"""

from enum import StrEnum

from pydantic import BaseModel, Field

from cairn.domain.glide_path import PRESERVATION_MIX
from cairn.domain.profiles import PROFILES, AssetClass, RiskProfile, equity_share
from cairn.domain.simulation import SimulationResult
from cairn.domain.stress import Replay, Scenario

Fraction = float  # 0.25 means 25%


class Topic(StrEnum):
    PROJECTION = "projection"
    ALLOCATION = "allocation"
    GLIDE_PATH = "glide_path"
    REBALANCE = "rebalance"
    STRESS_TEST = "stress_test"
    LEDGER_ENTRY = "ledger_entry"
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


FactsModel = (
    ProjectionFacts
    | AllocationFacts
    | GlidePathFacts
    | RebalanceFacts
    | StressTestFacts
    | LedgerEntryFacts
)

FACT_MODELS: dict[Topic, type[FactsModel]] = {
    Topic.PROJECTION: ProjectionFacts,
    Topic.ALLOCATION: AllocationFacts,
    Topic.GLIDE_PATH: GlidePathFacts,
    Topic.REBALANCE: RebalanceFacts,
    Topic.STRESS_TEST: StressTestFacts,
    Topic.LEDGER_ENTRY: LedgerEntryFacts,
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
