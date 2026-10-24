"""Risk profiles, model allocations, capital-market assumptions and the risk questionnaire.

Pure data and functions, no I/O.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

Language = Literal["en", "fr"]


class AssetClass(StrEnum):
    GLOBAL_EQUITY = "global_equity"
    EMERGING_EQUITY = "emerging_equity"
    EURO_GOV_BONDS = "euro_gov_bonds"
    MONEY_MARKET = "money_market"


ASSET_CLASSES: tuple[AssetClass, ...] = tuple(AssetClass)
Weights = dict[AssetClass, float]


@dataclass(frozen=True)
class AssetAssumption:
    expected_return: float  # expected annual return, arithmetic
    volatility: float  # annual standard deviation


# ILLUSTRATIVE capital-market assumptions for a demo. They are round, plausible long-run
# figures, not forecasts, and they are not calibrated to any data source.
ASSUMPTIONS: dict[AssetClass, AssetAssumption] = {
    AssetClass.GLOBAL_EQUITY: AssetAssumption(expected_return=0.065, volatility=0.15),
    AssetClass.EMERGING_EQUITY: AssetAssumption(expected_return=0.075, volatility=0.21),
    AssetClass.EURO_GOV_BONDS: AssetAssumption(expected_return=0.030, volatility=0.06),
    AssetClass.MONEY_MARKET: AssetAssumption(expected_return=0.020, volatility=0.01),
}

# Correlations between annual returns, in ASSET_CLASSES order. Also illustrative.
CORRELATIONS: tuple[tuple[float, ...], ...] = (
    # global eq, emerging eq, gov bonds, money market
    (1.00, 0.75, 0.10, 0.00),
    (0.75, 1.00, 0.05, 0.00),
    (0.10, 0.05, 1.00, 0.20),
    (0.00, 0.00, 0.20, 1.00),
)


class RiskProfile(StrEnum):
    PRUDENT = "prudent"
    MODERATE = "moderate"
    BALANCED = "balanced"
    DYNAMIC = "dynamic"
    BOLD = "bold"


# Ordered from most prudent to most risk-tolerant.
PROFILE_ORDER: tuple[RiskProfile, ...] = tuple(RiskProfile)


@dataclass(frozen=True)
class ProfileInfo:
    name: str
    description: str
    weights: Weights


def _w(global_eq: float, emerging_eq: float, bonds: float, money: float) -> Weights:
    return {
        AssetClass.GLOBAL_EQUITY: global_eq,
        AssetClass.EMERGING_EQUITY: emerging_eq,
        AssetClass.EURO_GOV_BONDS: bonds,
        AssetClass.MONEY_MARKET: money,
    }


PROFILES: dict[RiskProfile, ProfileInfo] = {
    RiskProfile.PRUDENT: ProfileInfo(
        "Prudent", "Mostly bonds and cash, small swings.", _w(0.15, 0.05, 0.50, 0.30)
    ),
    RiskProfile.MODERATE: ProfileInfo(
        "Moderate", "A cautious mix that still aims to grow.", _w(0.30, 0.05, 0.45, 0.20)
    ),
    RiskProfile.BALANCED: ProfileInfo(
        "Balanced", "Growth and safety in similar parts.", _w(0.45, 0.10, 0.35, 0.10)
    ),
    RiskProfile.DYNAMIC: ProfileInfo(
        "Dynamic", "Mostly shares, accepts bigger swings.", _w(0.60, 0.15, 0.20, 0.05)
    ),
    RiskProfile.BOLD: ProfileInfo(
        "Bold", "Almost all shares, for long horizons.", _w(0.75, 0.20, 0.05, 0.00)
    ),
}


def equity_share(weights: Weights) -> float:
    return weights[AssetClass.GLOBAL_EQUITY] + weights[AssetClass.EMERGING_EQUITY]


# --- Questionnaire -------------------------------------------------------------------------


@dataclass(frozen=True)
class Option:
    id: str
    text: dict[Language, str]
    score: int


@dataclass(frozen=True)
class Question:
    id: str
    text: dict[Language, str]
    options: tuple[Option, ...]  # ordered from most prudent (lowest score) to most risk-tolerant


def _o(option_id: str, score: int, en: str, fr: str) -> Option:
    return Option(id=option_id, text={"en": en, "fr": fr}, score=score)


QUESTIONS: tuple[Question, ...] = (
    Question(
        "horizon",
        {"en": "When will you need this money?", "fr": "Quand aurez-vous besoin de cet argent ?"},
        (
            _o("lt3", 0, "In less than 3 years", "Dans moins de 3 ans"),
            _o("3to5", 1, "In 3 to 5 years", "Dans 3 à 5 ans"),
            _o("5to10", 2, "In 5 to 10 years", "Dans 5 à 10 ans"),
            _o("10to20", 3, "In 10 to 20 years", "Dans 10 à 20 ans"),
            _o("gt20", 4, "In more than 20 years", "Dans plus de 20 ans"),
        ),
    ),
    Question(
        "income_stability",
        {"en": "How stable is your income?", "fr": "Vos revenus sont-ils stables ?"},
        (
            _o("unstable", 0, "Irregular or uncertain", "Irréguliers ou incertains"),
            _o("somewhat", 2, "Mostly stable", "Plutôt stables"),
            _o("stable", 4, "Very stable", "Très stables"),
        ),
    ),
    Question(
        "drop_reaction",
        {
            "en": "Your investments fall by 20% in a few months. What do you do?",
            "fr": "Vos placements baissent de 20 % en quelques mois. Que faites-vous ?",
        },
        (
            _o("sell_all", 0, "Sell everything", "Je vends tout"),
            _o("sell_some", 1, "Sell part of it", "J'en vends une partie"),
            _o("wait", 3, "Wait it out", "J'attends"),
            _o("buy_more", 4, "Invest more", "J'investis davantage"),
        ),
    ),
    Question(
        "experience",
        {"en": "Have you invested before?", "fr": "Avez-vous déjà investi ?"},
        (
            _o("none", 0, "Never", "Jamais"),
            _o("savings", 1, "Only savings accounts", "Seulement des livrets"),
            _o("funds", 3, "Funds or ETFs", "Des fonds ou des ETF"),
            _o("active", 4, "Shares, regularly", "Des actions, régulièrement"),
        ),
    ),
    Question(
        "share_of_savings",
        {
            "en": "What share of your savings is this goal?",
            "fr": "Quelle part de votre épargne représente cet objectif ?",
        },
        (
            _o("most", 0, "Most of it", "La majeure partie"),
            _o("half", 2, "About half", "Environ la moitié"),
            _o("small", 4, "A small part", "Une petite partie"),
        ),
    ),
    Question(
        "goal_flexibility",
        {
            "en": "Could you delay the goal or lower the amount if needed?",
            "fr": "Pourriez-vous décaler l'objectif ou réduire le montant si besoin ?",
        },
        (
            _o("no", 0, "No, it is fixed", "Non, il est fixe"),
            _o("a_little", 2, "A little", "Un peu"),
            _o("yes", 4, "Yes, easily", "Oui, facilement"),
        ),
    ),
)

MAX_SCORE = sum(max(o.score for o in q.options) for q in QUESTIONS)

# Upper bound (inclusive) of the total score for each profile, from most prudent upward.
_PROFILE_THRESHOLDS: tuple[tuple[int, RiskProfile], ...] = (
    (4, RiskProfile.PRUDENT),
    (9, RiskProfile.MODERATE),
    (14, RiskProfile.BALANCED),
    (19, RiskProfile.DYNAMIC),
    (MAX_SCORE, RiskProfile.BOLD),
)


class QuestionnaireError(ValueError):
    pass


def total_score(answers: dict[str, str]) -> int:
    """Sum the scores of the chosen options. Every question must be answered."""
    expected = {q.id for q in QUESTIONS}
    missing = expected - answers.keys()
    unknown = answers.keys() - expected
    if missing:
        raise QuestionnaireError(f"Missing answers for: {', '.join(sorted(missing))}")
    if unknown:
        raise QuestionnaireError(f"Unknown questions: {', '.join(sorted(unknown))}")
    total = 0
    for question in QUESTIONS:
        scores = {o.id: o.score for o in question.options}
        chosen = answers[question.id]
        if chosen not in scores:
            raise QuestionnaireError(f"Unknown option '{chosen}' for question '{question.id}'")
        total += scores[chosen]
    return total


def profile_for_score(score: int) -> RiskProfile:
    for upper, profile in _PROFILE_THRESHOLDS:
        if score <= upper:
            return profile
    return RiskProfile.BOLD


def score_questionnaire(answers: dict[str, str]) -> RiskProfile:
    return profile_for_score(total_score(answers))
