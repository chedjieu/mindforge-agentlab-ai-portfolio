"""E2E and quality smokes for WAIP (LangSmith-ready)."""

from __future__ import annotations

import json
import os
import uuid
from typing import Any

from langgraph.types import Command

# Force fake model for deterministic CI
os.environ.setdefault("WAIP_MODEL", "fake")
os.environ.setdefault("WAIP_EMBEDDINGS", "fake")

from app.graph import build_graph_with_backends
from app.llm import reset_llm_cache
from app.rag import hybrid_search


def e2e_paycheck_leave() -> dict[str, Any]:
    reset_llm_cache()
    graph = build_graph_with_backends()
    thread = {"configurable": {"thread_id": str(uuid.uuid4())}}
    init = {
        "associate_id": "A1001",
        "abac": {
            "country": "US",
            "state": "AR",
            "department": "Pharmacy",
            "role": "Pharmacy Tech",
            "bu": "US Stores",
            "store": "1001",
        },
        "query": (
            "My paycheck is short because I took medical leave last week. "
            "Can you explain why and open a payroll ticket if necessary?"
        ),
        "step_log": [],
        "evidence": [],
        "worker_results": {},
        "ticket_ids": [],
    }
    result = graph.invoke(init, config=thread)
    if graph.get_state(thread).tasks:
        result = graph.invoke(Command(resume={"approved": True, "note": "eval"}), config=thread)

    ok = (
        bool(result.get("final_response"))
        and bool(result.get("citations"))
        and bool(result.get("ticket_ids"))
        and (result.get("judges") or {}).get("validator", {}).get("pass", False)
    )
    return {
        "name": "e2e_paycheck_leave",
        "pass": ok,
        "tickets": result.get("ticket_ids"),
        "citation_count": len(result.get("citations") or []),
        "workers": result.get("workers"),
    }


def retrieval_smoke() -> dict[str, Any]:
    hits = hybrid_search(
        "payroll discrepancy medical leave unpaid hours",
        abac={"country": "US", "state": "AR", "department": "Pharmacy"},
        top_k=3,
    )
    return {"name": "retrieval_smoke", "pass": len(hits) >= 1, "hits": [h["doc_id"] for h in hits]}


def abac_smoke() -> dict[str, Any]:
    ca = hybrid_search(
        "California sick leave overlay",
        abac={"country": "US", "state": "CA", "department": "Fulfillment"},
        domain="leave",
        top_k=5,
    )
    ar = hybrid_search(
        "California sick leave overlay",
        abac={"country": "US", "state": "AR", "department": "Pharmacy"},
        domain="leave",
        top_k=5,
    )
    ca_ids = {h["doc_id"] for h in ca}
    # CA associate should be able to see CA overlay; AR may not
    return {
        "name": "abac_smoke",
        "pass": any("ca_leave" in i for i in ca_ids),
        "ca_hits": list(ca_ids),
        "ar_hits": [h["doc_id"] for h in ar],
    }


def run_all() -> dict[str, Any]:
    results = [e2e_paycheck_leave(), retrieval_smoke(), abac_smoke()]
    summary = {
        "pass": all(r["pass"] for r in results),
        "results": results,
        "langsmith": bool(os.getenv("LANGCHAIN_API_KEY")),
    }
    return summary


if __name__ == "__main__":
    out = run_all()
    print(json.dumps(out, indent=2))
    raise SystemExit(0 if out["pass"] else 1)
