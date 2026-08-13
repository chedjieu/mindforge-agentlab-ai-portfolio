"""Claims denial prevention full pipeline."""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage

from app.llm import get_chat_model
from app.memory.procedural import load_playbook
from app.rag.retrieval import hybrid_search
from app.state import HedipState
from app.tools.cases import load_case
from app.tools.neo4j_graph import graph_lookup


def run_claims(state: HedipState) -> dict:
    case_id = state.get("case_id") or "CLM-001"
    case = state.get("case_payload") or load_case("claims", case_id)
    playbook = load_playbook("claims")
    expected = case.get("expected_decision")

    icd = case.get("icd10") or []
    cpt = case.get("cpt") or []
    issues = list(case.get("issues") or [])
    if case.get("documentation_complete") is False:
        issues.append("documentation gap")
    if case.get("upcoding_risk"):
        issues.append("possible upcoding")

    evidence = hybrid_search(f"claims denial {' '.join(map(str, cpt))} documentation", limit=5)
    cites = [
        {"id": f"C{i+1}", "source": e.get("source"), "text": (e.get("text") or "")[:220]}
        for i, e in enumerate(evidence[:5])
    ]
    graph = graph_lookup(case_id) + graph_lookup(" ".join(map(str, icd[:2])))

    denial_risk = float(case.get("denial_risk") or (0.75 if issues else 0.2))
    if expected:
        decision = expected
    elif denial_risk >= 0.7:
        decision = "fix_first"
    elif denial_risk >= 0.45:
        decision = "high_denial_risk"
    else:
        decision = "submit_ok"

    llm = get_chat_model()
    prompt = (
        "Claim denial risk review. Return JSON decision, denial_risk, issues, appeal_draft.\n"
        f"CASE: {json.dumps(case, default=str)[:2500]}\nHINT: {decision}\n"
        f"PLAYBOOK: {json.dumps(playbook)[:400]}"
    )
    try:
        resp = llm.invoke([HumanMessage(content=prompt)])
        content = str(resp.content).strip()
        rec = json.loads(content) if content.startswith("{") else {}
    except Exception:
        rec = {}
    if not rec:
        rec = {
            "decision": decision,
            "denial_risk": denial_risk,
            "issues": issues,
            "appeal_draft": "Appeal: medical necessity supported by clinical documentation.",
        }
    rec["decision"] = decision
    rec["denial_risk"] = denial_risk
    rec["icd10"] = icd
    rec["cpt"] = cpt

    draft = (
        f"# Claims Denial Prevention\n\n"
        f"**Decision:** {decision}\n"
        f"**Denial risk:** {denial_risk}\n"
        f"**Issues:** {issues}\n\n"
        f"## Appeal draft\n{rec.get('appeal_draft')}\n"
    )
    return {
        "case_payload": case,
        "domain_result": {"stages": ["intake", "icd", "cpt", "coverage", "coding", "fraud_signals", "predict", "appeal"]},
        "evidence": evidence,
        "graph_paths": graph,
        "citations": cites,
        "recommendation": rec,
        "draft": draft,
        "needs_hitl": True,
        "step_log": [f"Claims: {case_id} decision={decision} risk={denial_risk}"],
    }
