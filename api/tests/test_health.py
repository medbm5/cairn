from fastapi.testclient import TestClient


def test_health_reports_database_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"


def test_request_id_is_generated(client: TestClient) -> None:
    response = client.get("/health")
    assert len(response.headers["X-Request-ID"]) == 32


def test_request_id_round_trip(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "abc-123"})
    assert response.headers["X-Request-ID"] == "abc-123"
