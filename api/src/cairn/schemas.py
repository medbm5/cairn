"""Pydantic request and response models."""

from typing import Literal

from pydantic import BaseModel, Field

from cairn.domain.profiles import AssetClass, RiskProfile

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
