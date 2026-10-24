from fastapi import APIRouter, HTTPException

from cairn.domain import profiles as p
from cairn.schemas import (
    Language,
    OptionOut,
    ProfileOut,
    QuestionnaireAnswers,
    QuestionnaireResult,
    QuestionOut,
)

router = APIRouter(tags=["profiles"])


def profile_out(profile: p.RiskProfile) -> ProfileOut:
    info = p.PROFILES[profile]
    return ProfileOut(
        key=profile,
        name=info.name,
        description=info.description,
        weights=info.weights,
        equity_share=round(p.equity_share(info.weights), 4),
    )


@router.get("/profiles")
def list_profiles() -> list[ProfileOut]:
    return [profile_out(profile) for profile in p.PROFILE_ORDER]


@router.get("/questionnaire")
def get_questionnaire(language: Language = "en") -> list[QuestionOut]:
    return [
        QuestionOut(
            id=q.id,
            text=q.text[language],
            options=[OptionOut(id=o.id, text=o.text[language]) for o in q.options],
        )
        for q in p.QUESTIONS
    ]


@router.post("/questionnaire/score")
def score(body: QuestionnaireAnswers) -> QuestionnaireResult:
    try:
        total = p.total_score(body.answers)
    except p.QuestionnaireError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return QuestionnaireResult(
        score=total, max_score=p.MAX_SCORE, profile=profile_out(p.profile_for_score(total))
    )
