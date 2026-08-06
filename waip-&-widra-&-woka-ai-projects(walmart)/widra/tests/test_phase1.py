"""Phase 1 smoke tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "widra"
    assert body["model"] == "fake"


def test_query_stub() -> None:
    resp = client.post("/query", json={"query": "What is the return policy for damaged goods?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "stub"
    assert body["answer"]
    assert len(body["citations"]) >= 1
