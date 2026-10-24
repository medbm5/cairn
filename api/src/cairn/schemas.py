"""Pydantic request and response models."""

from typing import Literal

from pydantic import BaseModel

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
