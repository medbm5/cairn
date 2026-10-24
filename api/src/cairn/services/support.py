"""Support view: find a client, read their account as one timeline, and answer questions from it.

The timeline is the ledger of every goal of the client, in time order. Each journal entry becomes
one event, and the goal's value after it is the running sum of its holding lines. Answers are
built only from these events: a month's balance change is split into market effect, deposits and
fees, computed here in cents, before any text is written.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from cairn.domain.profiles import ASSET_CLASSES, AssetClass
from cairn.explain.facts import SupportAnswerFacts
from cairn.models import Goal, JournalEntry, JournalLine, User
from cairn.services import ledger

HOLDING_PREFIX = "holding:"


class ClientNotFoundError(LookupError):
    def __init__(self, client_id: int) -> None:
        super().__init__(f"Client {client_id} does not exist.")


@dataclass(frozen=True)
class TimelineEvent:
    id: int  # the journal entry's id
    type: str  # deposit, fee, market or rebalance (the entry's kind)
    at: datetime
    goal_id: int
    goal_name: str
    # Change of the goal's value: positive for deposits and market gains, negative for fees and
    # market losses. A rebalance does not change the value; its amount is the money it moved.
    amount_cents: int
    value_change_cents: int
    goal_value_after_cents: int
    by_asset: dict[AssetClass, int]  # signed change of each holding

    @property
    def month(self) -> tuple[int, int]:
        return self.at.year, self.at.month

    def payload(self) -> dict[str, object]:
        """A short machine-readable description of the event."""
        changes = {asset: cents for asset, cents in self.by_asset.items() if cents != 0}
        if self.type == "rebalance":
            return {"moved_cents": self.amount_cents, "transfers": changes}
        return {"by_asset": changes}


# --- Clients ---


def search_clients(
    session: Session, query: str, page: int, page_size: int
) -> tuple[list[tuple[User, int]], int]:
    """Clients whose name or email contains the query (case-insensitive), with their goal count.

    Returns (rows for the page, total matches).
    """
    conditions = []
    if query.strip():
        needle = query.strip().lower()
        conditions.append(
            or_(
                func.lower(User.name).contains(needle, autoescape=True),
                func.lower(User.email).contains(needle, autoescape=True),
            )
        )
    total = session.scalar(select(func.count(User.id)).where(*conditions)) or 0
    goal_count = (
        select(func.count(Goal.id)).where(Goal.user_id == User.id).correlate(User).scalar_subquery()
    )
    rows = session.execute(
        select(User, goal_count)
        .where(*conditions)
        .order_by(User.name, User.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return [(user, count) for user, count in rows], total


def get_client(session: Session, client_id: int) -> User:
    user = session.get(User, client_id)
    if user is None:
        raise ClientNotFoundError(client_id)
    return user


def client_goals(session: Session, client: User) -> list[Goal]:
    return list(session.scalars(select(Goal).where(Goal.user_id == client.id).order_by(Goal.id)))


# --- Timeline ---


def _account_kind(line: JournalLine) -> str:
    return line.account.kind


def build_timeline(session: Session, client: User) -> list[TimelineEvent]:
    """Every ledger entry of the client's goals, oldest first (ties keep posting order)."""
    goals = {goal.id: goal for goal in client_goals(session, client)}
    if not goals:
        return []
    rows = session.scalars(
        select(JournalEntry)
        .where(JournalEntry.goal_id.in_(goals))
        .options(selectinload(JournalEntry.lines).selectinload(JournalLine.account))
        .order_by(JournalEntry.created_at, JournalEntry.id)
    )
    values = dict.fromkeys(goals, 0)
    events = []
    for entry in rows:
        by_asset = dict.fromkeys(ASSET_CLASSES, 0)
        for line in entry.lines:
            kind = _account_kind(line)
            if kind.startswith(HOLDING_PREFIX):
                by_asset[AssetClass(kind.removeprefix(HOLDING_PREFIX))] += line.amount_cents
        change = sum(by_asset.values())
        values[entry.goal_id] += change
        moved = sum(cents for cents in by_asset.values() if cents > 0)
        events.append(
            TimelineEvent(
                id=entry.id,
                type=entry.kind,
                at=entry.created_at,
                goal_id=entry.goal_id,
                goal_name=goals[entry.goal_id].name,
                amount_cents=moved if entry.kind == "rebalance" else change,
                value_change_cents=change,
                goal_value_after_cents=values[entry.goal_id],
                by_asset=by_asset,
            )
        )
    return events


def filter_timeline(
    events: Sequence[TimelineEvent], start: date | None, end: date | None
) -> list[TimelineEvent]:
    """Events between two dates, both included."""
    return [
        event
        for event in events
        if (start is None or event.at.date() >= start) and (end is None or event.at.date() <= end)
    ]


# --- Summary ---


@dataclass(frozen=True)
class GoalSummary:
    goal: Goal
    balance_cents: int
    contributed_cents: int
    fees_cents: int


@dataclass(frozen=True)
class ClientSummary:
    client: User
    goals: list[GoalSummary]
    profile: str | None  # the profile of the goal holding the most money
    total_balance_cents: int
    total_contributed_cents: int
    total_fees_cents: int
    last_activity: datetime | None


def summarize(session: Session, client: User) -> ClientSummary:
    goals = []
    for goal in client_goals(session, client):
        balances = ledger.account_balances(session, goal)
        goals.append(
            GoalSummary(
                goal=goal,
                balance_cents=sum(ledger.holdings(session, goal).values()),
                contributed_cents=-balances.get(ledger.EXTERNAL_BANK, 0),
                fees_cents=balances.get(ledger.FEES, 0),
            )
        )
    last_activity = session.scalar(
        select(func.max(JournalEntry.created_at)).join(Goal).where(Goal.user_id == client.id)
    )
    largest = max(goals, key=lambda g: g.balance_cents, default=None)
    return ClientSummary(
        client=client,
        goals=goals,
        profile=largest.goal.profile if largest else None,
        total_balance_cents=sum(g.balance_cents for g in goals),
        total_contributed_cents=sum(g.contributed_cents for g in goals),
        total_fees_cents=sum(g.fees_cents for g in goals),
        last_activity=last_activity,
    )


# --- Month decomposition ---


@dataclass(frozen=True)
class MonthBreakdown:
    year: int
    month: int
    start_balance_cents: int
    end_balance_cents: int
    market_effect_cents: int
    deposits_cents: int
    fees_cents: int  # money taken, so positive
    market_by_asset_cents: dict[AssetClass, int]
    event_ids: list[int]
    rebalanced: bool

    @property
    def change_cents(self) -> int:
        return self.end_balance_cents - self.start_balance_cents


class UnexplainedChangeError(ValueError):
    """The month's events do not account for the whole balance change."""


def month_breakdown(events: Sequence[TimelineEvent], year: int, month: int) -> MonthBreakdown:
    """Split the change of the client's total balance over one month into its parts.

    Only deposits, fees and market movements change the value of holdings; a rebalance moves money
    between them and nets to zero. So the parts add up to the change exactly, in cents. This is
    checked here, so a new kind of entry can never be silently left out of an answer.
    """
    before = [e for e in events if e.month < (year, month)]
    during = [e for e in events if e.month == (year, month)]
    start = sum(e.value_change_cents for e in before)
    end = start + sum(e.value_change_cents for e in during)

    def total(kind: str) -> int:
        return sum(e.value_change_cents for e in during if e.type == kind)

    market_by_asset = dict.fromkeys(ASSET_CLASSES, 0)
    for event in during:
        if event.type == "market":
            for asset, cents in event.by_asset.items():
                market_by_asset[asset] += cents
    breakdown = MonthBreakdown(
        year=year,
        month=month,
        start_balance_cents=start,
        end_balance_cents=end,
        market_effect_cents=total("market"),
        deposits_cents=total("deposit"),
        fees_cents=-total("fee"),
        market_by_asset_cents=market_by_asset,
        event_ids=[e.id for e in during],
        rebalanced=any(e.type == "rebalance" for e in during),
    )
    parts = breakdown.market_effect_cents + breakdown.deposits_cents - breakdown.fees_cents
    if parts != breakdown.change_cents:
        raise UnexplainedChangeError(
            f"{year}-{month:02d}: parts add up to {parts}, change is {breakdown.change_cents}."
        )
    return breakdown


# --- Questions ---

MONTH_WORDS: dict[str, int] = {}
for _number, _names in enumerate(
    [
        ("january", "jan", "janvier", "janv"),
        ("february", "feb", "février", "fevrier", "févr", "fevr"),
        ("march", "mar", "mars"),
        ("april", "apr", "avril", "avr"),
        ("may", "mai"),
        ("june", "jun", "juin"),
        ("july", "jul", "juillet", "juil"),
        ("august", "aug", "août", "aout"),
        ("september", "sep", "sept", "septembre"),
        ("october", "oct", "octobre"),
        ("november", "nov", "novembre"),
        ("december", "dec", "décembre", "decembre", "déc"),
    ],
    start=1,
):
    for _name in _names:
        MONTH_WORDS[_name] = _number

WORD = re.compile(r"[a-zàâäçéèêëîïôöùûüÿœ]+")
YEAR = re.compile(r"\b(20\d\d)\b")
REBALANCE_WORDS = re.compile(r"rebalanc|rééquilibr|reequilibr")
FALL_WORDS = re.compile(r"\b(down|drop|dropped|fall|fell|lost|loss|lose|baiss|perdu|chut)")


def month_in_question(question: str) -> tuple[int | None, int | None]:
    """(year, month) named in the question; either may be None."""
    text = question.lower()
    month = next((MONTH_WORDS[w] for w in WORD.findall(text) if w in MONTH_WORDS), None)
    year_match = YEAR.search(text)
    return (int(year_match.group(1)) if year_match else None), month


def latest_month_named(events: Sequence[TimelineEvent], month: int) -> tuple[int, int]:
    """The most recent occurrence of this calendar month, up to the client's latest activity."""
    latest_year, latest_month = events[-1].month
    return (latest_year if month <= latest_month else latest_year - 1), month


def largest_fall(events: Sequence[TimelineEvent]) -> tuple[int, int] | None:
    """The month whose total value change was the most negative, if any month fell."""
    changes: dict[tuple[int, int], int] = {}
    for event in events:
        changes[event.month] = changes.get(event.month, 0) + event.value_change_cents
    worst = min(changes.items(), key=lambda item: item[1], default=None)
    return worst[0] if worst and worst[1] < 0 else None


@dataclass(frozen=True)
class Answerable:
    facts: SupportAnswerFacts
    breakdown: MonthBreakdown
    event_ids: list[int]


class NothingToAnswerError(ValueError):
    pass


def answer_facts(
    events: Sequence[TimelineEvent], question: str, month: tuple[int, int] | None
) -> Answerable:
    """Pick what the question is about and build its facts from the timeline only.

    The month comes from the request, else from a month named in the question (its latest
    occurrence when no year is given), else the worst month for "why did it go down" questions,
    else the latest month with activity.
    """
    if not events:
        raise NothingToAnswerError("This client has no activity yet.")
    focus: Literal["month_change", "last_rebalance"] = "month_change"
    if month is None:
        year, named = month_in_question(question)
        if named is not None:
            month = (year, named) if year is not None else latest_month_named(events, named)
        elif REBALANCE_WORDS.search(question.lower()):
            focus = "last_rebalance"
        elif FALL_WORDS.search(question.lower()):
            month = largest_fall(events)
    if month is None:
        month = events[-1].month

    breakdown = month_breakdown(events, *month)
    rebalances = [e for e in events if e.type == "rebalance"]
    last = rebalances[-1] if rebalances else None
    facts = SupportAnswerFacts(
        question=question,
        focus=focus,
        year=breakdown.year,
        month=breakdown.month,
        start_balance_cents=breakdown.start_balance_cents,
        end_balance_cents=breakdown.end_balance_cents,
        change_cents=breakdown.change_cents,
        market_effect_cents=breakdown.market_effect_cents,
        deposits_cents=breakdown.deposits_cents,
        fees_cents=breakdown.fees_cents,
        market_by_asset_cents=breakdown.market_by_asset_cents,
        rebalanced_this_month=breakdown.rebalanced,
        last_rebalance_year=last.at.year if last else None,
        last_rebalance_month=last.at.month if last else None,
        last_rebalance_day=last.at.day if last else None,
        last_rebalance_moved_cents=last.amount_cents if last else None,
    )
    rebalance_ids = [last.id] if last else []
    return Answerable(
        facts=facts,
        breakdown=breakdown,
        event_ids=rebalance_ids if focus == "last_rebalance" else breakdown.event_ids,
    )
