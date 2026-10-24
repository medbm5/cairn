from collections.abc import Iterator
from datetime import date
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from cairn.explain.client import GeneratedExplanation, OpenAIExplainer
from cairn.models import Goal, JournalEntry, User
from cairn.routers import explain as explain_router
from cairn.services import ledger, support
from tests.test_seed import load_seed

TODAY = date(2026, 10, 24)
SHOCK_MONTH = "2026-03"  # Camille Martin's crash: seven months before October 2026


@pytest.fixture
def seeded(session: Session) -> Session:
    load_seed().seed(session, TODAY)
    return session


@pytest.fixture
def api(client: TestClient, seeded: Session) -> Iterator[TestClient]:
    """The API over the seeded demo, without an OpenAI key."""
    explain_router.response_cache.clear()
    explain_router.rate_limiter.reset()
    client.app.dependency_overrides[explain_router.get_explainer] = lambda: None  # type: ignore[attr-defined]
    yield client


def client_id(session: Session, email: str) -> int:
    user = session.scalars(select(User).where(User.email == email)).one()
    return user.id


def months_of(events: list[support.TimelineEvent]) -> list[tuple[int, int]]:
    return sorted({event.month for event in events})


# --- Timeline ---


def test_timeline_is_ordered_and_complete_versus_the_ledger(seeded: Session) -> None:
    for user in seeded.scalars(select(User)):
        events = support.build_timeline(seeded, user)
        goal_ids = list(seeded.scalars(select(Goal.id).where(Goal.user_id == user.id)))
        entry_ids = set(
            seeded.scalars(select(JournalEntry.id).where(JournalEntry.goal_id.in_(goal_ids)))
        )
        assert [(e.at, e.id) for e in events] == sorted((e.at, e.id) for e in events)
        assert {e.id for e in events} == entry_ids
        assert len(events) == len(entry_ids)
        # The running value of each goal ends at what its holdings are worth today.
        for goal in seeded.scalars(select(Goal).where(Goal.user_id == user.id)):
            last = [e for e in events if e.goal_id == goal.id][-1]
            assert last.goal_value_after_cents == sum(ledger.holdings(seeded, goal).values())


def test_timeline_has_every_kind_of_event(seeded: Session) -> None:
    camille = seeded.get(User, client_id(seeded, "camille.martin@example.com"))
    assert camille is not None
    kinds = {event.type for event in support.build_timeline(seeded, camille)}
    assert kinds == {"deposit", "fee", "market", "rebalance"}


def test_every_month_splits_exactly_into_its_parts(seeded: Session) -> None:
    for user in seeded.scalars(select(User)):
        events = support.build_timeline(seeded, user)
        previous_end = 0
        for year, month in months_of(events):
            b = support.month_breakdown(events, year, month)
            assert b.market_effect_cents + b.deposits_cents - b.fees_cents == b.change_cents
            assert b.change_cents == b.end_balance_cents - b.start_balance_cents
            assert sum(b.market_by_asset_cents.values()) == b.market_effect_cents
            assert b.start_balance_cents == previous_end
            previous_end = b.end_balance_cents


def test_endpoint_lists_the_timeline_between_dates(api: TestClient, seeded: Session) -> None:
    cid = client_id(seeded, "hugo.petit@example.com")
    everything = api.get(f"/support/clients/{cid}/timeline").json()
    june = api.get(
        f"/support/clients/{cid}/timeline", params={"from": "2026-06-01", "to": "2026-06-30"}
    ).json()
    assert len(everything) > len(june) > 0
    assert all(event["date"].startswith("2026-06") for event in june)
    fee = next(e for e in june if e["type"] == "fee")
    assert fee["amount_cents"] == -5_00
    assert fee["goal"]["name"] == "Sailing trip"
    assert sum(fee["payload"]["by_asset"].values()) == -5_00
    rebalances = [e for e in everything if e["type"] == "rebalance"]
    for event in rebalances:
        assert event["amount_cents"] == event["payload"]["moved_cents"] > 0

    bad = api.get(
        f"/support/clients/{cid}/timeline", params={"from": "2026-07-01", "to": "2026-06-01"}
    )
    assert bad.status_code == 422


# --- Clients ---


def test_search_by_name_or_email_with_pages(api: TestClient) -> None:
    by_name = api.get("/support/clients", params={"query": "CAMILLE"}).json()
    assert [c["name"] for c in by_name["items"]] == ["Camille Martin"]
    by_email = api.get("/support/clients", params={"query": "petit@example"}).json()
    assert [c["name"] for c in by_email["items"]] == ["Hugo Petit"]

    first = api.get("/support/clients", params={"page_size": 2}).json()
    second = api.get("/support/clients", params={"page_size": 2, "page": 2}).json()
    assert first["total"] == 6  # the demo user and five clients
    assert len(first["items"]) == 2 and len(second["items"]) == 2
    assert {c["id"] for c in first["items"]}.isdisjoint(c["id"] for c in second["items"])
    thomas = api.get("/support/clients", params={"query": "thomas"}).json()["items"][0]
    assert thomas["goal_count"] == 2


def test_client_summary(api: TestClient, seeded: Session) -> None:
    cid = client_id(seeded, "thomas.bernard@example.com")
    summary = api.get(f"/support/clients/{cid}").json()
    assert summary["name"] == "Thomas Bernard"
    assert len(summary["goals"]) == 2
    assert summary["profile"] == "bold"  # the retirement goal holds the most money
    assert summary["total_balance_cents"] == sum(g["balance_cents"] for g in summary["goals"])
    assert summary["total_contributed_cents"] == sum(
        g["contributed_cents"] for g in summary["goals"]
    )
    assert summary["total_fees_cents"] > 0
    assert summary["last_activity"].startswith("2026-09")


def test_demo_goals_page_does_not_show_support_clients(api: TestClient) -> None:
    assert len(api.get("/goals").json()) == 3


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/support/clients/999"),
        ("get", "/support/clients/999/timeline"),
        ("post", "/support/clients/999/ask"),
    ],
)
def test_unknown_client_returns_404(api: TestClient, method: str, path: str) -> None:
    kwargs: dict[str, Any] = {"json": {"question": "Why?"}} if method == "post" else {}
    response = getattr(api, method)(path, **kwargs)
    assert response.status_code == 404
    assert response.json()["detail"] == "Client 999 does not exist."


# --- Questions ---


def test_why_did_it_go_down_finds_the_crash_and_splits_it(api: TestClient, seeded: Session) -> None:
    cid = client_id(seeded, "camille.martin@example.com")
    response = api.post(
        f"/support/clients/{cid}/ask", json={"question": "Why did the balance go down?"}
    )
    assert response.status_code == 200
    body = response.json()
    b = body["breakdown"]
    assert body["focus"] == "month_change"
    assert b["month"] == SHOCK_MONTH
    assert b["change_cents"] < 0 and b["market_effect_cents"] < b["change_cents"]
    assert b["market_effect_cents"] + b["deposits_cents"] - b["fees_cents"] == b["change_cents"]
    assert b["end_balance_cents"] - b["start_balance_cents"] == b["change_cents"]

    timeline = api.get(f"/support/clients/{cid}/timeline").json()
    in_month = [e["id"] for e in timeline if e["date"].startswith(SHOCK_MONTH)]
    assert body["event_ids"] == in_month


def test_fallback_answer_without_an_openai_key(api: TestClient, seeded: Session) -> None:
    cid = client_id(seeded, "camille.martin@example.com")
    body = api.post(
        f"/support/clients/{cid}/ask",
        json={"question": "Why did the balance go down in March?", "language": "en"},
    ).json()
    answer = body["answer"]
    assert answer["source"] == "fallback"
    assert body["breakdown"]["month"] == SHOCK_MONTH
    assert "March 2026" in answer["body"]
    change = abs(body["breakdown"]["change_cents"])
    assert f"a fall of €{change / 100:,.2f}" in answer["body"]
    fees = body["breakdown"]["fees_cents"]
    assert f"Fees: -€{fees / 100:,.2f}" in answer["body"]


def test_month_in_the_request_wins(api: TestClient, seeded: Session) -> None:
    cid = client_id(seeded, "lea.dubois@example.com")
    body = api.post(
        f"/support/clients/{cid}/ask",
        json={"question": "What happened?", "month": "2026-05", "language": "fr"},
    ).json()
    assert body["breakdown"]["month"] == "2026-05"
    assert "mai 2026" in body["answer"]["body"]


def test_last_rebalance_question(api: TestClient, seeded: Session) -> None:
    cid = client_id(seeded, "camille.martin@example.com")
    body = api.post(
        f"/support/clients/{cid}/ask", json={"question": "When was the last rebalance?"}
    ).json()
    timeline = api.get(f"/support/clients/{cid}/timeline").json()
    last = [e for e in timeline if e["type"] == "rebalance"][-1]
    assert body["focus"] == "last_rebalance"
    assert body["event_ids"] == [last["id"]]
    assert f"€{last['amount_cents'] / 100:,.2f}" in body["answer"]["body"]


def test_ai_answer_with_a_made_up_figure_falls_back(client: TestClient, seeded: Session) -> None:
    explain_router.response_cache.clear()
    explain_router.rate_limiter.reset()
    explainer = MagicMock(spec=OpenAIExplainer)
    explainer.generate.return_value = GeneratedExplanation(
        title="March", body="Markets fell by 40% so she lost €9,999.", analogy=None, terms_used=[]
    )
    client.app.dependency_overrides[explain_router.get_explainer] = lambda: explainer  # type: ignore[attr-defined]
    cid = client_id(seeded, "camille.martin@example.com")
    body = client.post(
        f"/support/clients/{cid}/ask", json={"question": "Why did it drop in March?"}
    ).json()
    assert explainer.generate.called
    assert body["answer"]["source"] == "fallback"


def test_client_without_activity_cannot_be_asked(api: TestClient, seeded: Session) -> None:
    newcomer = User(name="New client", email="new@example.com")
    seeded.add(newcomer)
    seeded.commit()
    response = api.post(f"/support/clients/{newcomer.id}/ask", json={"question": "Why?"})
    assert response.status_code == 409
    assert api.get(f"/support/clients/{newcomer.id}/timeline").json() == []
