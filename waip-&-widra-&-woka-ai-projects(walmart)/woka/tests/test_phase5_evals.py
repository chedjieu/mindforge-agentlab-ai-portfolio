"""Phase 5 — judges, injection, audit/evaluate/feedback APIs."""

from __future__ import annotations

import os

os.environ["WOKA_MODEL"] = "fake"
os.environ["WOKA_EMBEDDINGS"] = "fake"

from fastapi.testclient import TestClient

from app.config import get_settings
from app.llm import reset_llm_cache
from app.main import app
from evals.injection_suite import run_injection_suite
from evals.judges import evaluate_answer

get_settings.cache_clear()
reset_llm_cache()
client = TestClient(app)

GOLDEN = (
    "Hurricane closed DCs in the Southeast. Which suppliers are affected, "
    "which products are delayed, what inventory exists within 300 miles, "
    "which contracts allow alternate sourcing, and which stores will stock out within 48 hours?"
)


def test_injection_suite_ge_95() -> None:
    result = run_injection_suite()
    assert result["pass"] is True
    assert result["block_rate"] >= 0.95


def test_health_phase5() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["phase"] >= 5
    assert "langsmith" in resp.json()


def test_chat_writes_audit_and_judges() -> None:
    resp = client.post(
        "/chat",
        json={"query": GOLDEN, "role": "analyst", "department": "Supply Chain", "region": "SE"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["audit_id"]
    assert body["judges"]
    assert body["judges"].get("pass") is True

    audit = client.get("/audit", params={"limit": 10})
    assert audit.status_code == 200
    items = audit.json()["items"]
    assert any(i.get("audit_id") == body["audit_id"] for i in items)


def test_evaluate_uc1() -> None:
    resp = client.post("/evaluate", json={"run_uc1": True, "query": GOLDEN})
    assert resp.status_code == 200
    body = resp.json()
    assert body["pass"] is True
    assert body["eval"]["gates"]["citation_accuracy"]["score"] > 0


def test_feedback() -> None:
    resp = client.post(
        "/feedback",
        json={"query": GOLDEN, "answer": "useful", "rating": 5, "comment": "good"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    listed = client.get("/audit", params={"action": "feedback"})
    assert listed.json()["count"] >= 1


def test_judge_heuristic_on_stub() -> None:
    result = evaluate_answer(
        query=GOLDEN,
        answer=(
            "Southeast DC closures (ATL-01, JAX-02) affect suppliers Acme Logistics. "
            "Inventory within 300 miles: TV-55-4K at MEM-03 (12400 units)."
        ),
        citations=[
            {
                "doc_id": "sql:inventory",
                "title": "Inventory",
                "snippet": "MEM-03 TV-55-4K 12400 Acme Logistics ATL-01",
                "source_type": "sql",
                "confidence": 0.95,
            }
        ],
        sql={
            "data": {
                "inventory_within_300mi": [{"location_id": "MEM-03", "sku": "TV-55-4K", "qty": 12400}],
                "affected_suppliers": [{"name": "Acme Logistics"}],
            }
        },
    )
    assert result["pass"] is True
