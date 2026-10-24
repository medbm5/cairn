from dataclasses import asdict
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Header, Response, status

from cairn.models import JournalEntry
from cairn.routers.goals import GoalDep, SessionDep
from cairn.schemas import (
    BalanceOut,
    DepositCreate,
    JournalEntryOut,
    JournalLineOut,
    ReconciliationOut,
)
from cairn.services import ledger

router = APIRouter(tags=["ledger"])

IdempotencyKey = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=200)]


def entry_out(entry: JournalEntry) -> JournalEntryOut:
    return JournalEntryOut(
        id=entry.id,
        goal_id=entry.goal_id,
        kind=entry.kind,
        description=entry.description,
        created_at=entry.created_at,
        lines=[
            JournalLineOut(account=line.account.kind, amount_cents=line.amount_cents)
            for line in entry.lines
        ],
    )


@router.post("/goals/{goal_id}/deposits", status_code=status.HTTP_201_CREATED)
def create_deposit(
    goal: GoalDep,
    body: DepositCreate,
    session: SessionDep,
    response: Response,
    idempotency_key: IdempotencyKey,
) -> JournalEntryOut:
    entry, created = ledger.deposit(
        session, goal, body.amount_cents, idempotency_key, today=date.today()
    )
    if not created:
        response.status_code = status.HTTP_200_OK
        response.headers["Idempotent-Replayed"] = "true"
    return entry_out(entry)


@router.get("/goals/{goal_id}/balance")
def get_balance(goal: GoalDep, session: SessionDep) -> BalanceOut:
    holdings = ledger.holdings(session, goal)
    total = sum(holdings.values())
    return BalanceOut(
        goal_id=goal.id,
        total_cents=total,
        contributed_cents=ledger.contributed_cents(session, goal),
        fees_cents=ledger.account_balances(session, goal).get(ledger.FEES, 0),
        holdings=holdings,
        weights={a: round(c / total, 4) if total else 0.0 for a, c in holdings.items()},
    )


@router.get("/goals/{goal_id}/entries")
def list_entries(goal: GoalDep, session: SessionDep) -> list[JournalEntryOut]:
    return [entry_out(entry) for entry in ledger.entries(session, goal)]


@router.get("/ledger/reconciliation")
def reconciliation(session: SessionDep) -> ReconciliationOut:
    return ReconciliationOut(**asdict(ledger.reconcile(session)))
