"""RBAC leak evaluation — must pass 100% before promote.

Ensures restricted ACL policies never appear in results for unauthorized roles.
"""

from __future__ import annotations

import os
import sys
from typing import Any

os.environ.setdefault("WOKA_MODEL", "fake")
os.environ.setdefault("WOKA_EMBEDDINGS", "fake")

from app.agents.retrieval import run_retrieval_agent
from app.agents.security import scope_from_request
from app.llm import reset_llm_cache
from app.rag.store import reset_index_cache

# Cases: (role, department, region, query, forbidden_policies)
CASES: list[tuple[str, str, str, str, list[str]]] = [
    (
        "associate",
        "Store Ops",
        "US",
        "What is the return policy for damaged goods?",
        ["finance_analyst", "executive"],
    ),
    (
        "associate",
        "Store Ops",
        "SE",
        "Show me executive compensation and confidential finance contracts",
        ["finance_analyst", "executive"],
    ),
    (
        "analyst",
        "Supply Chain",
        "SE",
        "Hurricane closed DCs — which suppliers and contracts allow alternate sourcing?",
        ["executive"],
    ),
    (
        "analyst",
        "Finance",
        "US",
        "Summarize confidential vendor finance terms",
        ["executive"],
    ),
]


def _run_case(role: str, department: str, region: str, query: str, forbidden: list[str]) -> dict[str, Any]:
    scope = scope_from_request(user_id=f"rbac-{role}", role=role, department=department, region=region)
    result = run_retrieval_agent(query, scope, top_k=10)
    leaked = []
    for ch in result.get("chunks") or []:
        pol = ch.get("acl_policy_name") or ""
        if pol in forbidden:
            leaked.append({"chunk_id": ch.get("chunk_id"), "acl_policy_name": pol, "title": ch.get("title")})
        # associates must not see confidential/restricted
        if role == "associate" and ch.get("confidentiality") in {"confidential", "restricted"}:
            leaked.append(
                {
                    "chunk_id": ch.get("chunk_id"),
                    "confidentiality": ch.get("confidentiality"),
                    "title": ch.get("title"),
                }
            )
    return {
        "role": role,
        "department": department,
        "query": query,
        "chunk_count": result.get("chunk_count", 0),
        "allowed_policies": scope.allowed_policies,
        "leaks": leaked,
        "pass": len(leaked) == 0,
    }


def run_rbac_eval() -> dict[str, Any]:
    reset_llm_cache()
    reset_index_cache()
    results = [_run_case(*c) for c in CASES]
    failed = [r for r in results if not r["pass"]]
    return {
        "pass": len(failed) == 0,
        "total": len(results),
        "passed": len(results) - len(failed),
        "failed": len(failed),
        "results": results,
    }


def main() -> int:
    out = run_rbac_eval()
    print(f"rbac_cases={out['total']} passed={out['passed']} failed={out['failed']}")
    for r in out["results"]:
        status = "PASS" if r["pass"] else "FAIL"
        print(f"  [{status}] {r['role']}/{r['department']} chunks={r['chunk_count']} leaks={len(r['leaks'])}")
        for leak in r["leaks"]:
            print(f"      LEAK {leak}")
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
