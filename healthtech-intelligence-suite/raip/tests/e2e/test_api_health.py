from fastapi.testclient import TestClient

from app.main import app


def test_health_and_ready() -> None:
    with TestClient(app) as client:
        assert client.get("/health").json()["status"] == "ok"
        assert client.get("/ready").json()["status"] == "ready"
        assert client.get("/metrics").status_code == 200
