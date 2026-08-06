"""Knowledge builder — hybrid RAG + GraphRAG."""

from __future__ import annotations

from app.tools.kg import lookup_entity, traverse_relations
from app.tools.retrieval import hybrid_search
from app.state import ForgeState

MAX_TOOLS = 8


def knowledge_builder_node(state: ForgeState) -> dict:
    domain = state.get("domain") or "agentic"
    client_id = state["client_id"]
    query = " ".join(
        str(state["raw_pack"].get(k) or "")
        for k in ("title", "body", "description")
    )
    evidence: list[dict] = []
    calls = 0

    chunks = hybrid_search(query=query, client_id=client_id, domain=domain)
    calls += 1
    for i, ch in enumerate(chunks[:4]):
        evidence.append({"id": f"ev-{i+1}", "type": "chunk", **ch})

    if calls < MAX_TOOLS:
        ent = lookup_entity(query=query, client_id=client_id, domain=domain)
        calls += 1
        if ent:
            evidence.append({"id": "ev-ent", "type": "entity", **ent})
            if calls < MAX_TOOLS:
                paths = traverse_relations(ent.get("id"), client_id=client_id)
                calls += 1
                if paths:
                    evidence.append({"id": "ev-graph", "type": "graph_paths", "paths": paths})

    if not evidence:
        evidence.append(
            {
                "id": "ev-1",
                "type": "chunk",
                "text": f"Baseline {domain} AWS Pattern playbook for {client_id}",
                "client_id": client_id,
                "score": 0.5,
            }
        )

    return {
        "evidence": evidence,
        "step_log": state["step_log"]
        + [f"knowledge_builder: {len(evidence)} evidence ({calls} tools)"],
    }
