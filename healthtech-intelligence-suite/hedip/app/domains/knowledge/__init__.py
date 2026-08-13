"""Enterprise knowledge Q&A full pipeline."""

from __future__ import annotations

from app.memory.procedural import load_playbook
from app.rag.retrieval import hybrid_search
from app.state import HedipState
from app.tools.cases import load_case
from app.tools.neo4j_graph import graph_lookup


def run_knowledge(state: HedipState) -> dict:
    case_id = state.get("case_id") or "KNOW-001"
    case = state.get("case_payload") or load_case("knowledge", case_id)
    query = state.get("query") or case.get("query") or "What is step therapy?"
    evidence = hybrid_search(query, limit=6)
    graph = graph_lookup(query)
    cites = [
        {"id": f"C{i+1}", "source": e.get("source"), "text": (e.get("text") or "")[:240]}
        for i, e in enumerate(evidence[:6])
    ]
    answer_bits = [e.get("text", "")[:300] for e in evidence[:3]]
    draft = (
        f"# Knowledge Answer\n\n**Question:** {query}\n\n"
        + "\n\n".join(f"- {b}" for b in answer_bits)
        + "\n\nCitations: "
        + ", ".join(c["id"] for c in cites)
    )
    if not answer_bits:
        draft = f"# Knowledge Answer\n\nNo corpus hit for: {query}\nSee playbook {load_playbook('knowledge')}"

    return {
        "case_payload": case,
        "domain_result": {"stages": ["plan", "retrieve", "graph", "synthesize", "cite"]},
        "evidence": evidence,
        "graph_paths": graph,
        "citations": cites,
        "recommendation": {"decision": "answered", "query": query},
        "draft": draft,
        "needs_hitl": False,
        "step_log": [f"Knowledge: {len(evidence)} chunks for query"],
    }
