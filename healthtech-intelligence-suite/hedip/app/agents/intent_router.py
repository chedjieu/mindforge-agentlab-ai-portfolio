"""Intent router — classify domain."""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage

from app.llm import get_chat_model
from app.state import Domain, HedipState

DOMAIN_HINTS: list[tuple[tuple[str, ...], Domain]] = [
    (("prior auth", "prior-auth", "authorization", "mri", "biologic", "medical necessity"), "prior_auth"),
    (("claim", "denial", "icd-10", "cpt", "appeal", "upcod"), "claims"),
    (("treatment plan", "cds", "medication plan", "chronic care"), "clinical_cds"),
    (("discharge", "care coord", "readmission", "home health"), "care_coord"),
    (("fraud", "phantom", "collusion", "waste", "abuse"), "fraud"),
    (("population", "sepsis", "risk strat", "cohort"), "pop_health"),
    (("coding", "documentation", "revenue cycle", "billing code"), "rcm"),
    (("policy", "what is", "guideline", "sop", "knowledge"), "knowledge"),
]

SENSITIVE = {"prior_auth", "claims", "clinical_cds", "fraud"}


def intent_router(state: HedipState) -> dict:
    if state.get("domain"):
        domain = state["domain"]
        return {
            "domain": domain,
            "sensitivity": "sensitive" if domain in SENSITIVE else "normal",
            "needs_hitl": domain in SENSITIVE,
            "intent": {"domain": domain, "source": "explicit"},
            "step_log": [f"Intent: explicit domain={domain}"],
        }

    query = (state.get("query") or "").lower()
    case_id = (state.get("case_id") or "").lower()
    blob = f"{query} {case_id}"
    for keys, domain in DOMAIN_HINTS:
        if any(k in blob for k in keys):
            return {
                "domain": domain,
                "sensitivity": "sensitive" if domain in SENSITIVE else "normal",
                "needs_hitl": domain in SENSITIVE,
                "intent": {"domain": domain, "source": "heuristic"},
                "step_log": [f"Intent: heuristic domain={domain}"],
            }

    try:
        llm = get_chat_model()
        prompt = (
            "Intent router: classify domain as one of prior_auth, claims, clinical_cds, "
            "care_coord, knowledge, fraud, pop_health, rcm. Return JSON "
            '{"domain":"...","sensitivity":"sensitive|normal"}.\n'
            f"QUERY: {state.get('query')}\nCASE: {state.get('case_id')}"
        )
        resp = llm.invoke([HumanMessage(content=prompt)])
        data = json.loads(str(resp.content))
        domain = data.get("domain") or "knowledge"
        return {
            "domain": domain,
            "sensitivity": data.get("sensitivity") or ("sensitive" if domain in SENSITIVE else "normal"),
            "needs_hitl": domain in SENSITIVE,
            "intent": {"domain": domain, "source": "llm"},
            "step_log": [f"Intent: llm domain={domain}"],
        }
    except Exception:
        return {
            "domain": "knowledge",
            "sensitivity": "normal",
            "needs_hitl": False,
            "intent": {"domain": "knowledge", "source": "fallback"},
            "step_log": ["Intent: fallback knowledge"],
        }
