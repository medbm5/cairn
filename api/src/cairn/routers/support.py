"""Support view for a customer-support agent: demo-scoped and without authentication (ADR 0004)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from cairn.domain.profiles import RiskProfile
from cairn.explain.client import OpenAIExplainer
from cairn.explain.facts import Topic
from cairn.explain.service import RateLimiter, ResponseCache, explain
from cairn.models import User
from cairn.routers.explain import get_cache, get_explainer, get_rate_limiter
from cairn.routers.goals import SessionDep
from cairn.schemas import (
    BreakdownOut,
    ClientListItem,
    ClientPage,
    ClientSummaryOut,
    GoalRef,
    GoalType,
    SupportAnswerOut,
    SupportAskRequest,
    SupportGoalOut,
    TimelineEventOut,
)
from cairn.services import support

router = APIRouter(prefix="/support", tags=["support"])


def client_or_404(session: SessionDep, client_id: int) -> User:
    try:
        return support.get_client(session, client_id)
    except support.ClientNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


ClientDep = Annotated[User, Depends(client_or_404)]


def event_out(event: support.TimelineEvent) -> TimelineEventOut:
    return TimelineEventOut(
        id=event.id,
        type=event.type,
        date=event.at,
        amount_cents=event.amount_cents,
        goal=GoalRef(id=event.goal_id, name=event.goal_name),
        goal_value_after_cents=event.goal_value_after_cents,
        payload=event.payload(),
    )


@router.get("/clients")
def search_clients(
    session: SessionDep,
    query: Annotated[str, Query(max_length=100)] = "",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> ClientPage:
    rows, total = support.search_clients(session, query, page, page_size)
    return ClientPage(
        items=[
            ClientListItem(id=user.id, name=user.name, email=user.email, goal_count=count)
            for user, count in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/clients/{client_id}")
def get_client(client: ClientDep, session: SessionDep) -> ClientSummaryOut:
    summary = support.summarize(session, client)
    return ClientSummaryOut(
        id=client.id,
        name=client.name,
        email=client.email,
        profile=RiskProfile(summary.profile) if summary.profile else None,
        total_balance_cents=summary.total_balance_cents,
        total_contributed_cents=summary.total_contributed_cents,
        total_fees_cents=summary.total_fees_cents,
        last_activity=summary.last_activity,
        goals=[
            SupportGoalOut(
                id=g.goal.id,
                name=g.goal.name,
                type=GoalType(g.goal.type),
                profile=RiskProfile(g.goal.profile),
                target_cents=g.goal.target_cents,
                target_date=g.goal.target_date,
                balance_cents=g.balance_cents,
                contributed_cents=g.contributed_cents,
                fees_cents=g.fees_cents,
            )
            for g in summary.goals
        ],
    )


@router.get("/clients/{client_id}/timeline")
def get_timeline(
    client: ClientDep,
    session: SessionDep,
    start: Annotated[date | None, Query(alias="from")] = None,
    end: Annotated[date | None, Query(alias="to")] = None,
) -> list[TimelineEventOut]:
    if start and end and start > end:
        raise HTTPException(status_code=422, detail="'from' must be on or before 'to'.")
    events = support.filter_timeline(support.build_timeline(session, client), start, end)
    return [event_out(event) for event in events]


@router.post("/clients/{client_id}/ask")
def ask(
    client: ClientDep,
    body: SupportAskRequest,
    request: Request,
    session: SessionDep,
    explainer: Annotated[OpenAIExplainer | None, Depends(get_explainer)],
    cache: Annotated[ResponseCache, Depends(get_cache)],
    limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> SupportAnswerOut:
    client_ip = request.client.host if request.client else "unknown"
    if not limiter.allow(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Too many questions in a short time. Wait a minute and try again.",
            headers={"Retry-After": str(int(limiter.window))},
        )
    month = None
    if body.month:
        year, month_number = body.month.split("-")
        month = (int(year), int(month_number))
    events = support.build_timeline(session, client)
    try:
        answerable = support.answer_facts(events, body.question, month)
    except support.NothingToAnswerError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    answer = explain(
        topic=Topic.SUPPORT_ANSWER,
        facts=answerable.facts,
        term=None,
        level="simple",
        language=body.language,
        explainer=explainer,
        cache=cache,
    )
    b = answerable.breakdown
    return SupportAnswerOut(
        answer=answer,
        focus=answerable.facts.focus,
        breakdown=BreakdownOut(
            month=f"{b.year:04d}-{b.month:02d}",
            start_balance_cents=b.start_balance_cents,
            end_balance_cents=b.end_balance_cents,
            change_cents=b.change_cents,
            market_effect_cents=b.market_effect_cents,
            deposits_cents=b.deposits_cents,
            fees_cents=b.fees_cents,
            market_by_asset_cents=b.market_by_asset_cents,
        ),
        event_ids=answerable.event_ids,
    )
