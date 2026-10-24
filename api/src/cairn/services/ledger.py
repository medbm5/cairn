"""Double-entry ledger: posting balanced entries, deposits, fees, balances and reconciliation.

Sign convention: a positive line increases the account's balance, a negative line decreases it.
Every entry's lines sum to zero, so the sum of all account balances is always zero. Money leaving
the person's bank account shows as a negative `external_bank` balance.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from cairn.domain.dates import months_between
from cairn.domain.glide_path import allocation_at
from cairn.domain.money import split_cents
from cairn.domain.profiles import ASSET_CLASSES, AssetClass, RiskProfile, Weights
from cairn.domain.rebalancing import max_drift, rebalance_transfers
from cairn.domain.simulation import monthly_asset_returns
from cairn.models import Account, Goal, JournalEntry, JournalLine

EXTERNAL_BANK = "external_bank"
CASH = "cash"
FEES = "fees"
MARKET = "market"  # counterpart of price movements: gains are negative here, losses positive


def holding(asset: AssetClass) -> str:
    return f"holding:{asset}"


class UnbalancedEntryError(ValueError):
    pass


class InsufficientFundsError(ValueError):
    pass


def get_account(session: Session, goal: Goal, kind: str) -> Account:
    account = session.scalars(
        select(Account).where(Account.goal_id == goal.id, Account.kind == kind)
    ).first()
    if account is None:
        account = Account(user_id=goal.user_id, goal_id=goal.id, kind=kind, balance_cents=0)
        session.add(account)
        session.flush()
    return account


def find_entry(session: Session, idempotency_key: str) -> JournalEntry | None:
    return session.scalars(
        select(JournalEntry).where(JournalEntry.idempotency_key == idempotency_key)
    ).first()


def post_entry(
    session: Session,
    *,
    goal: Goal,
    kind: str,
    idempotency_key: str,
    description: str,
    lines: Sequence[tuple[str, int]],
    created_at: datetime | None = None,
) -> tuple[JournalEntry, bool]:
    """Post one balanced entry in a single transaction.

    `lines` are (account kind, signed cents). Returns (entry, created). If an entry with the same
    idempotency key exists, it is returned unchanged with created=False. `created_at` defaults to
    now; the seed script sets it to replay past months.
    """
    existing = find_entry(session, idempotency_key)
    if existing is not None:
        return existing, False

    lines = [(account, amount) for account, amount in lines if amount != 0]
    if sum(amount for _, amount in lines) != 0:
        raise UnbalancedEntryError(f"Entry '{description}' does not balance: {lines}")
    if len(lines) < 2:
        raise UnbalancedEntryError(f"Entry '{description}' needs at least two non-zero lines.")

    try:
        entry = JournalEntry(
            goal_id=goal.id, kind=kind, idempotency_key=idempotency_key, description=description
        )
        if created_at is not None:
            entry.created_at = created_at
        session.add(entry)
        deltas: dict[str, int] = {}
        for account_kind, amount in lines:
            deltas[account_kind] = deltas.get(account_kind, 0) + amount
        accounts = {kind: get_account(session, goal, kind) for kind in deltas}
        for account_kind, amount in lines:
            entry.lines.append(
                JournalLine(account_id=accounts[account_kind].id, amount_cents=amount)
            )
        for account_kind, delta in deltas.items():
            # SQL-side increment, so concurrent postings cannot lose an update.
            accounts[account_kind].balance_cents = Account.balance_cents + delta
        session.commit()
    except IntegrityError:
        # Another request with the same key won the race: return its entry.
        session.rollback()
        existing = find_entry(session, idempotency_key)
        if existing is None:
            raise
        return existing, False
    session.refresh(entry)
    return entry, True


def current_allocation(goal: Goal, today: date) -> Weights:
    return allocation_at(RiskProfile(goal.profile), months_between(today, goal.target_date))


def deposit(
    session: Session,
    goal: Goal,
    amount_cents: int,
    idempotency_key: str,
    today: date,
    created_at: datetime | None = None,
) -> tuple[JournalEntry, bool]:
    """Move money from the person's bank and invest it according to the current allocation."""
    if amount_cents <= 0:
        raise ValueError("A deposit must be positive.")
    split = split_cents(amount_cents, current_allocation(goal, today), ASSET_CLASSES)
    lines = [(EXTERNAL_BANK, -amount_cents)]
    lines += [(holding(asset), cents) for asset, cents in split.items()]
    return post_entry(
        session,
        goal=goal,
        kind="deposit",
        idempotency_key=f"deposit:{goal.id}:{idempotency_key}",
        description=f"Deposit of {amount_cents} cents",
        lines=lines,
        created_at=created_at,
    )


def holdings(session: Session, goal: Goal) -> dict[AssetClass, int]:
    balances = account_balances(session, goal)
    return {asset: balances.get(holding(asset), 0) for asset in ASSET_CLASSES}


def charge_fee(
    session: Session,
    goal: Goal,
    amount_cents: int,
    idempotency_key: str,
    created_at: datetime | None = None,
) -> tuple[JournalEntry, bool]:
    """Take a fee from the holdings, in proportion to their current values."""
    current = holdings(session, goal)
    total = sum(current.values())
    if amount_cents <= 0:
        raise ValueError("A fee must be positive.")
    if amount_cents > total:
        raise InsufficientFundsError("The fee is larger than the goal's holdings.")
    weights = {asset: float(cents) for asset, cents in current.items()}
    split = split_cents(amount_cents, weights, ASSET_CLASSES)
    lines = [(FEES, amount_cents)]
    lines += [(holding(asset), -cents) for asset, cents in split.items()]
    return post_entry(
        session,
        goal=goal,
        kind="fee",
        idempotency_key=f"fee:{goal.id}:{idempotency_key}",
        description=f"Fee of {amount_cents} cents",
        lines=lines,
        created_at=created_at,
    )


def mark_to_market(
    session: Session,
    goal: Goal,
    year: int,
    month: int,
    created_at: datetime | None = None,
    returns: Mapping[AssetClass, float] | None = None,
) -> JournalEntry | None:
    """Apply one month of seeded market returns to the goal's holdings (once per month).

    `returns` replaces the seeded returns, so the demo seed can stage a market shock. Returns the
    entry, or None when there is nothing to revalue.
    """
    key = f"mtm:{goal.id}:{year:04d}-{month:02d}"
    existing = find_entry(session, key)
    if existing is not None:
        return existing
    if returns is None:
        returns = monthly_asset_returns(seed=goal.id, month=year * 12 + month)
    moves = {a: round(cents * returns[a]) for a, cents in holdings(session, goal).items()}
    lines = [(holding(a), cents) for a, cents in moves.items()]
    lines.append((MARKET, -sum(moves.values())))
    if all(cents == 0 for cents in moves.values()):
        return None
    entry, _ = post_entry(
        session,
        goal=goal,
        kind="market",
        idempotency_key=key,
        description=f"Market movements for {year:04d}-{month:02d}",
        lines=lines,
        created_at=created_at,
    )
    return entry


@dataclass(frozen=True)
class RebalanceOutcome:
    entry: JournalEntry | None
    created: bool
    drift_before: float
    target: Weights


def rebalance(
    session: Session, goal: Goal, as_of: date, created_at: datetime | None = None
) -> RebalanceOutcome:
    """Rebalance back to the current glide-path allocation if any class drifted more than 5 points.

    Idempotent per goal and date: a second call on the same date returns the first entry.
    """
    key = f"rebalance:{goal.id}:{as_of.isoformat()}"
    target = current_allocation(goal, as_of)
    current = holdings(session, goal)
    drift = max_drift(current, target)
    existing = find_entry(session, key)
    if existing is not None:
        return RebalanceOutcome(existing, created=False, drift_before=drift, target=target)
    transfers = rebalance_transfers(current, target)
    if not transfers:
        return RebalanceOutcome(None, created=False, drift_before=drift, target=target)
    entry, created = post_entry(
        session,
        goal=goal,
        kind="rebalance",
        idempotency_key=key,
        description=f"Rebalance on {as_of.isoformat()} (largest drift {drift:.1%})",
        lines=[(holding(a), cents) for a, cents in transfers.items()],
        created_at=created_at,
    )
    return RebalanceOutcome(entry, created=created, drift_before=drift, target=target)


def account_balances(session: Session, goal: Goal) -> dict[str, int]:
    rows = session.execute(
        select(Account.kind, Account.balance_cents).where(Account.goal_id == goal.id)
    )
    return {kind: balance for kind, balance in rows}


def contributed_cents(session: Session, goal: Goal) -> int:
    """Money brought in from the bank so far (the bank account's balance, sign flipped)."""
    return -account_balances(session, goal).get(EXTERNAL_BANK, 0)


def entries(session: Session, goal: Goal, kind: str | None = None) -> list[JournalEntry]:
    query = select(JournalEntry).where(JournalEntry.goal_id == goal.id)
    if kind is not None:
        query = query.where(JournalEntry.kind == kind)
    return list(session.scalars(query.order_by(JournalEntry.id.desc())))


@dataclass(frozen=True)
class Reconciliation:
    ok: bool
    entries_checked: int
    accounts_checked: int
    unbalanced_entry_ids: list[int]
    mismatched_account_ids: list[int]
    total_cents: int  # sum of every line in the ledger; always zero when healthy


def reconcile(session: Session) -> Reconciliation:
    """Check every entry balances and every stored account balance equals the sum of its lines."""
    entry_count = session.scalar(select(func.count(JournalEntry.id))) or 0
    unbalanced = list(
        session.scalars(
            select(JournalLine.entry_id)
            .group_by(JournalLine.entry_id)
            .having(func.sum(JournalLine.amount_cents) != 0)
        )
    )
    line_sums = (
        select(JournalLine.account_id, func.sum(JournalLine.amount_cents).label("total"))
        .group_by(JournalLine.account_id)
        .subquery()
    )
    rows = session.execute(
        select(Account.id, Account.balance_cents, func.coalesce(line_sums.c.total, 0)).outerjoin(
            line_sums, line_sums.c.account_id == Account.id
        )
    ).all()
    mismatched = [account_id for account_id, stored, summed in rows if stored != summed]
    total = int(session.scalar(select(func.coalesce(func.sum(JournalLine.amount_cents), 0))) or 0)
    return Reconciliation(
        ok=not unbalanced and not mismatched and total == 0,
        entries_checked=entry_count,
        accounts_checked=len(rows),
        unbalanced_entry_ids=unbalanced,
        mismatched_account_ids=mismatched,
        total_cents=total,
    )
