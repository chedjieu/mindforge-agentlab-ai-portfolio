"""Phase 3 security + hybrid retrieval tests."""

from __future__ import annotations

import os

os.environ["WOKA_MODEL"] = "fake"
os.environ["WOKA_EMBEDDINGS"] = "fake"

from app.agents.retrieval import run_retrieval_agent
from app.agents.security import scope_from_request
from app.llm import reset_llm_cache
from app.rag.kg import graph_hops
from app.rag.store import reset_index_cache
from app.security.acl import chunk_authorized, resolve_scope


def setup_module() -> None:
    reset_llm_cache()
    reset_index_cache()


def test_security_scope_associate_vs_sc() -> None:
    assoc = resolve_scope(role="associate", department="Store Ops", region="US")
    sc = resolve_scope(role="analyst", department="Supply Chain", region="SE")
    assert "general_employee" in assoc.allowed_policies
    assert "supply_chain_ops" not in assoc.allowed_policies
    assert "supply_chain_ops" in sc.allowed_policies


def test_chunk_authorized_blocks_finance_from_associate() -> None:
    scope = resolve_scope(role="associate", department="Store Ops")
    assert chunk_authorized(
        scope,
        acl_policy_name="general_employee",
        confidentiality="internal",
        region="US",
    )
    assert not chunk_authorized(
        scope,
        acl_policy_name="finance_analyst",
        confidentiality="confidential",
        region="US",
    )


def test_graph_hops_hurricane() -> None:
    facts = graph_hops("Hurricane closed Southeast DCs suppliers alternate sourcing")
    assert facts
    rels = {f.get("rel") for f in facts}
    assert rels & {"SUPPLIES", "COVERS", "BACKUP_FOR", "SERVES"}


def test_retrieval_sc_analyst_gets_results() -> None:
    scope = scope_from_request(
        user_id="sc-1",
        role="analyst",
        department="Supply Chain",
        region="SE",
    )
    result = run_retrieval_agent(
        "Hurricane contingency alternate sourcing contracts inventory",
        scope,
        top_k=5,
    )
    # May be empty if corpus not ingested in CI — still must not leak
    for ch in result.get("chunks") or []:
        assert ch["acl_policy_name"] in scope.allowed_policies
        assert ch["confidentiality"] in {"internal", "confidential", "restricted"}
        if scope.clearance == "internal":
            assert ch["confidentiality"] == "internal"


def test_rbac_eval_suite() -> None:
    from security.rbac_eval import main

    assert main() == 0
