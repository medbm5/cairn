"""Pydantic request and response models."""

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Any, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from cairn.domain.dates import months_between
from cairn.domain.profiles import AssetClass, RiskProfile
from cairn.domain.stress import Scenario
from cairn.explain.facts import FACT_MODELS, FactsModel, Topic
from cairn.explain.glossary import GLOSSARY
from cairn.explain.service import Explanation

Language = Literal["en", "fr"]


class Health(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "unavailable"]
    environment: str


# --- Profiles and questionnaire ---


class ProfileOut(BaseModel):
    key: RiskProfile
    name: str
    description: str
    weights: dict[AssetClass, float]
    equity_share: float


class OptionOut(BaseModel):
    id: str
    text: str


class QuestionOut(BaseModel):
    id: str
    text: str
    options: list[OptionOut]


class QuestionnaireAnswers(BaseModel):
    answers: dict[str, str]


class QuestionnaireResult(BaseModel):
    score: int
    max_score: int
    profile: ProfileOut


# --- Simulation ---

MAX_AMOUNT_CENTS = 100_000_000_00  # 100 million euros
MAX_MONTHLY_CENTS = 1_000_000_00  # 1 million euros a month


class SimulationRequest(BaseModel):
    initial_cents: int = Field(ge=0, le=MAX_AMOUNT_CENTS)
    monthly_contribution_cents: int = Field(ge=0, le=MAX_MONTHLY_CENTS)
    horizon_months: int = Field(ge=12, le=480, description="Between 1 and 40 years.")
    profile: RiskProfile
    target_cents: int | None = Field(default=None, ge=0, le=MAX_AMOUNT_CENTS)
    glide_path: bool = Field(default=False, description="Shift toward safety near the goal.")
    paths: int = Field(default=5_000, ge=100, le=10_000)
    seed: int | None = Field(default=None, ge=0, le=2**32 - 1)


class SimulationResponse(BaseModel):
    seed: int
    paths: int
    months: list[int]
    p10: list[int]
    p25: list[int]
    p50: list[int]
    p75: list[int]
    p90: list[int]
    contributed: list[int]
    success_probability: float | None


# --- Glide path ---


class GlidePathPoint(BaseModel):
    year: int
    months_remaining: int
    weights: dict[AssetClass, float]
    equity_share: float


class GlidePathResponse(BaseModel):
    profile: RiskProfile
    horizon_months: int
    points: list[GlidePathPoint]


# --- Goals ---


class GoalType(StrEnum):
    RETIREMENT = "retirement"
    HOME = "home"
    SAFETY_NET = "safety_net"
    STUDIES = "studies"
    OTHER = "other"


def _check_target_date(value: date) -> date:
    months = months_between(date.today(), value)
    if months < 12:
        raise ValueError("The target date must be at least one year from today.")
    if months > 480:
        raise ValueError("The target date must be at most 40 years from today.")
    return value


GoalName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
TargetDate = Annotated[date, AfterValidator(_check_target_date)]
TargetCents = Annotated[int, Field(gt=0, le=MAX_AMOUNT_CENTS)]
MonthlyCents = Annotated[int, Field(ge=0, le=MAX_MONTHLY_CENTS)]


class GoalCreate(BaseModel):
    name: GoalName
    type: GoalType
    target_cents: TargetCents
    target_date: TargetDate
    monthly_contribution_cents: MonthlyCents
    profile: RiskProfile


class GoalUpdate(BaseModel):
    name: GoalName | None = None
    type: GoalType | None = None
    target_cents: TargetCents | None = None
    target_date: TargetDate | None = None
    monthly_contribution_cents: MonthlyCents | None = None
    profile: RiskProfile | None = None


class GoalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: GoalType
    target_cents: int
    target_date: date
    monthly_contribution_cents: int
    profile: RiskProfile
    created_at: datetime


class GoalProjection(BaseModel):
    goal_id: int
    horizon_months: int
    start_cents: int
    target_cents: int
    simulation: SimulationResponse


# --- Ledger ---


class DepositCreate(BaseModel):
    amount_cents: int = Field(gt=0, le=MAX_AMOUNT_CENTS)


class JournalLineOut(BaseModel):
    account: str
    amount_cents: int


class JournalEntryOut(BaseModel):
    id: int
    goal_id: int
    kind: str
    description: str
    created_at: datetime
    lines: list[JournalLineOut]


class BalanceOut(BaseModel):
    goal_id: int
    total_cents: int
    contributed_cents: int
    fees_cents: int
    holdings: dict[AssetClass, int]
    weights: dict[AssetClass, float]


class ReconciliationOut(BaseModel):
    ok: bool
    entries_checked: int
    accounts_checked: int
    unbalanced_entry_ids: list[int]
    mismatched_account_ids: list[int]
    total_cents: int


# --- Rebalancing ---


class RebalanceRequest(BaseModel):
    as_of: date | None = Field(default=None, description="Defaults to today.")


class RebalanceOut(BaseModel):
    rebalanced: bool
    created: bool
    drift_before: float
    threshold: float
    target_weights: dict[AssetClass, float]
    entry: JournalEntryOut | None


# --- Stress tests ---


class ReplayOut(BaseModel):
    values: list[int]
    max_drawdown: float
    months_to_recover: int | None
    rebalances: int


class StressTestOut(BaseModel):
    scenario: Scenario
    name: str
    description: str
    months: int
    start_cents: int
    weights: dict[AssetClass, float]
    without_rebalancing: ReplayOut
    with_rebalancing: ReplayOut


# --- Explanations ---


class ExplainRequest(BaseModel):
    topic: Topic
    facts: dict[str, Any] | None = None
    term: str | None = None
    level: Literal["simple", "more_detail"] = "simple"
    language: Language = "en"

    @model_validator(mode="after")
    def check_topic_inputs(self) -> Self:
        if self.topic == Topic.TERM:
            if self.term not in GLOSSARY:
                raise ValueError(f"Unknown term '{self.term}'. Known terms: {sorted(GLOSSARY)}.")
        elif self.facts is None:
            raise ValueError(f"Topic '{self.topic}' needs facts.")
        else:
            FACT_MODELS[self.topic].model_validate(self.facts)
        return self

    def parsed_facts(self) -> FactsModel | None:
        if self.topic == Topic.TERM or self.facts is None:
            return None
        return FACT_MODELS[self.topic].model_validate(self.facts)


# --- Support view ---


class ClientListItem(BaseModel):
    id: int
    name: str
    email: str | None
    goal_count: int


class ClientPage(BaseModel):
    items: list[ClientListItem]
    total: int
    page: int
    page_size: int


class SupportGoalOut(BaseModel):
    id: int
    name: str
    type: GoalType
    profile: RiskProfile
    target_cents: int
    target_date: date
    balance_cents: int
    contributed_cents: int
    fees_cents: int


class ClientSummaryOut(BaseModel):
    id: int
    name: str
    email: str | None
    profile: RiskProfile | None = Field(description="Profile of the goal holding the most money.")
    total_balance_cents: int
    total_contributed_cents: int
    total_fees_cents: int
    last_activity: datetime | None
    goals: list[SupportGoalOut]


class GoalRef(BaseModel):
    id: int
    name: str


class TimelineEventOut(BaseModel):
    id: int = Field(description="The journal entry's id.")
    type: str = Field(description="deposit, fee, market or rebalance.")
    date: datetime
    amount_cents: int = Field(
        description="Change of the goal's value; for a rebalance, the money moved between "
        "investments (the value does not change)."
    )
    goal: GoalRef
    goal_value_after_cents: int
    payload: dict[str, Any]


MonthKey = Annotated[str, StringConstraints(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]


class SupportAskRequest(BaseModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]
    month: MonthKey | None = Field(default=None, description="YYYY-MM; inferred when omitted.")
    language: Language = "en"


class BreakdownOut(BaseModel):
    month: MonthKey
    start_balance_cents: int
    end_balance_cents: int
    change_cents: int
    market_effect_cents: int
    deposits_cents: int
    fees_cents: int
    market_by_asset_cents: dict[AssetClass, int]


class SupportAnswerOut(BaseModel):
    answer: Explanation
    focus: Literal["month_change", "last_rebalance"]
    breakdown: BreakdownOut
    event_ids: list[int] = Field(description="Timeline events the answer is about.")


# --- Observability ---


class RouteStats(BaseModel):
    method: str
    route: str
    count: int
    errors: int
    p50_ms: float
    p95_ms: float


class RequestOut(BaseModel):
    at: datetime
    method: str
    route: str
    path: str
    status: int
    duration_ms: float
    request_id: str | None


class ApiStats(BaseModel):
    requests: int
    status_counts: dict[str, int]
    error_rate: float
    p50_ms: float
    p95_ms: float
    routes: list[RouteStats]
    recent: list[RequestOut]


class TopicStats(BaseModel):
    topic: str
    explanations: int
    ai: int
    cache: int
    fallback: int
    calls: int
    input_tokens: int
    output_tokens: int
    cost_usd: float


class LlmCallOut(BaseModel):
    at: datetime
    topic: str
    model: str
    ok: bool
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    latency_ms: float
    cost_usd: float | None
    error: str | None
    request_id: str | None


class LlmStats(BaseModel):
    model: str
    enabled: bool
    explanations: int
    sources: dict[str, int]
    fallback_reasons: dict[str, int]
    calls: int
    failed_calls: int
    input_tokens: int
    output_tokens: int
    reasoning_tokens: int
    cost_usd: float | None
    avg_latency_ms: float
    topics: list[TopicStats]
    recent: list[LlmCallOut]


class LogLineOut(BaseModel):
    at: datetime
    level: str
    event: str
    logger: str | None
    request_id: str | None
    fields: dict[str, Any]


class ObservabilityStats(BaseModel):
    since: datetime
    api: ApiStats
    llm: LlmStats
    logs: list[LogLineOut]
