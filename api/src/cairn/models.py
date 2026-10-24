"""SQLAlchemy models. Money is always stored as integer cents."""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from cairn.db import Base

__all__ = ["Account", "Base", "Goal", "JournalEntry", "JournalLine", "User"]


class User(Base):
    """A demo client. The first user is the visitor's demo user; the others are invented clients
    for the support view. The API is demo-scoped and has no authentication (ADR 0004)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255), unique=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    goals: Mapped[list["Goal"]] = relationship(back_populates="user")


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    type: Mapped[str] = mapped_column(String(20))
    target_cents: Mapped[int] = mapped_column(BigInteger)
    target_date: Mapped[date] = mapped_column(Date)
    monthly_contribution_cents: Mapped[int] = mapped_column(BigInteger)
    profile: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="goals")
    # Deleting a goal removes its whole ledger: entries balance on their own, so the remaining
    # ledger still reconciles.
    entries: Mapped[list["JournalEntry"]] = relationship(
        back_populates="goal", cascade="all, delete-orphan"
    )
    accounts: Mapped[list["Account"]] = relationship(
        back_populates="goal", cascade="all, delete-orphan"
    )


class Account(Base):
    """A ledger account of a goal. Kinds: external_bank, cash, fees, holding:<asset_class>."""

    __tablename__ = "accounts"
    __table_args__ = (UniqueConstraint("goal_id", "kind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    # Denormalised running balance; reconciliation checks it equals the sum of the lines.
    balance_cents: Mapped[int] = mapped_column(BigInteger, default=0)

    goal: Mapped[Goal] = relationship(back_populates="accounts")
    lines: Mapped[list["JournalLine"]] = relationship(back_populates="account")


class JournalEntry(Base):
    """One business event. Its lines always sum to zero."""

    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    goal_id: Mapped[int] = mapped_column(ForeignKey("goals.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    goal: Mapped[Goal] = relationship(back_populates="entries")
    lines: Mapped[list["JournalLine"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan", order_by="JournalLine.id"
    )


class JournalLine(Base):
    """A signed movement on one account: positive increases the account balance."""

    __tablename__ = "journal_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("journal_entries.id"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    amount_cents: Mapped[int] = mapped_column(BigInteger)

    entry: Mapped[JournalEntry] = relationship(back_populates="lines")
    account: Mapped[Account] = relationship(back_populates="lines")
