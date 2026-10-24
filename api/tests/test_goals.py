from datetime import date

import pytest
from fastapi.testclient import TestClient

from cairn.domain.dates import months_between


def in_years(years: int) -> str:
    today = date.today()
    return today.replace(year=today.year + years, day=min(today.day, 28)).isoformat()


def goal_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "name": "A flat in Lyon",
        "type": "home",
        "target_cents": 6_000_000,
        "target_date": in_years(8),
        "monthly_contribution_cents": 50_000,
        "profile": "balanced",
    }
    return body | overrides


def test_create_list_get_update_delete(client: TestClient) -> None:
    created = client.post("/goals", json=goal_body())
    assert created.status_code == 201
    goal = created.json()
    assert goal["name"] == "A flat in Lyon"

    assert [g["id"] for g in client.get("/goals").json()] == [goal["id"]]
    assert client.get(f"/goals/{goal['id']}").json()["target_cents"] == 6_000_000

    updated = client.patch(f"/goals/{goal['id']}", json={"monthly_contribution_cents": 70_000})
    assert updated.status_code == 200
    assert updated.json()["monthly_contribution_cents"] == 70_000
    assert updated.json()["name"] == "A flat in Lyon"

    assert client.delete(f"/goals/{goal['id']}").status_code == 204
    assert client.get(f"/goals/{goal['id']}").status_code == 404


def test_unknown_goal_returns_404(client: TestClient) -> None:
    response = client.get("/goals/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Goal 9999 does not exist."
    assert client.patch("/goals/9999", json={"name": "x"}).status_code == 404
    assert client.delete("/goals/9999").status_code == 404
    assert client.get("/goals/9999/projection").status_code == 404


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"target_date": in_years(0)}, "at least one year from today"),
        ({"target_date": in_years(45)}, "at most 40 years from today"),
        ({"target_cents": 0}, "greater than 0"),
        ({"monthly_contribution_cents": -1}, "greater than or equal to 0"),
        ({"name": "   "}, "at least 1 character"),
        ({"profile": "reckless"}, "'prudent', 'moderate', 'balanced', 'dynamic' or 'bold'"),
    ],
)
def test_validation_errors_are_clear(
    client: TestClient, overrides: dict[str, object], message: str
) -> None:
    response = client.post("/goals", json=goal_body(**overrides))
    assert response.status_code == 422
    assert message in str(response.json()["detail"])


def test_projection_uses_glide_path_to_goal_date(client: TestClient) -> None:
    goal = client.post("/goals", json=goal_body()).json()
    response = client.get(f"/goals/{goal['id']}/projection", params={"paths": 500})
    assert response.status_code == 200
    body = response.json()
    expected_horizon = months_between(date.today(), date.fromisoformat(goal["target_date"]))
    assert body["horizon_months"] == expected_horizon
    assert len(body["simulation"]["p50"]) == expected_horizon + 1
    assert 0 <= body["simulation"]["success_probability"] <= 1
    # Same goal, same default seed: the projection is stable between calls.
    again = client.get(f"/goals/{goal['id']}/projection", params={"paths": 500}).json()
    assert again == body


def test_months_between() -> None:
    assert months_between(date(2026, 1, 15), date(2027, 1, 15)) == 12
    assert months_between(date(2026, 1, 15), date(2027, 1, 14)) == 11
    assert months_between(date(2026, 3, 1), date(2026, 1, 1)) == -2
