"""Master supervisor — route to domain or shared post-steps."""

from __future__ import annotations

from app.state import HedipState

DOMAIN_NODES = {
    "prior_auth",
    "claims",
    "clinical_cds",
    "care_coord",
    "knowledge",
    "fraud",
    "pop_health",
    "rcm",
}


def master_supervisor(state: HedipState) -> dict:
    if state.get("blocked"):
        nxt = "publish"
    elif state.get("approval") == "rejected":
        nxt = "END"
    elif not state.get("domain"):
        nxt = "intent_router"
    elif not state.get("domain_result"):
        domain = state.get("domain") or "knowledge"
        nxt = domain if domain in DOMAIN_NODES else "knowledge"
    elif state.get("safety_score") is None:
        nxt = "shared_judge"
    elif state.get("needs_hitl") and state.get("approval") == "pending":
        nxt = "hitl"
    elif state.get("approval") in ("approved", "edited", "auto") and not state.get("published"):
        nxt = "publish"
    elif not state.get("needs_hitl") and not state.get("published"):
        # auto path for non-sensitive
        nxt = "publish"
    else:
        nxt = "END"

    return {"next": nxt, "step_log": [f"Supervisor: route -> {nxt}"]}
