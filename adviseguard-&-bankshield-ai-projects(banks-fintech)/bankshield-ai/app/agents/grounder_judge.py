"""Grounder + safety judge — claim–evidence scoring; may force revise."""

from __future__ import annotations

from app.state import InvestigationState


def _score_grounding(state: InvestigationState) -> float:
    rec = state.get("recommendation") or {}
    evidence = state.get("evidence") or []
    citations = state.get("reg_citations") or []
    eids = set(rec.get("evidence_ids") or [])
    real_eids = {e.get("id") for e in evidence if e.get("id")}
    cited_ok = len(eids & real_eids) / max(len(eids), 1) if eids else 0.5

    has_regs = any(c.get("id") not in (None, "EMPTY") for c in citations)
    has_summary = bool(rec.get("summary"))
    has_reasoning = bool(rec.get("reasoning"))
    invented_penalty = 0.0
    for eid in eids:
        if eid not in real_eids:
            invented_penalty += 0.15

    score = 0.35 * cited_ok
    score += 0.2 if has_regs else 0.0
    score += 0.2 if has_summary else 0.0
    score += 0.15 if has_reasoning else 0.0
    score += 0.1 if state.get("risk_score") is not None else 0.0
    score -= invented_penalty
    return round(max(0.0, min(1.0, score)), 3)


def grounder_judge_node(state: InvestigationState) -> dict:
    revise_count = int(state.get("revise_count") or 0)
    score = _score_grounding(state)

    # Cross-provider judge hook (fake/no-op enrichment)
    try:
        from app.eval.judge_client import judge_recommendation

        judged = judge_recommendation(state)
        if judged is not None:
            score = round(0.6 * score + 0.4 * float(judged), 3)
    except Exception:
        pass

    if score < 0.7 and revise_count < 2:
        return {
            "recommendation": None,
            "grounding_score": None,
            "revise_count": revise_count + 1,
            "step_log": state["step_log"]
            + [f"GrounderJudge: score={score} -> revise #{revise_count + 1}"],
        }

    approval = state.get("approval") or "auto"
    if score < 0.7:
        approval = "pending"

    return {
        "grounding_score": score,
        "approval": approval,
        "step_log": state["step_log"]
        + [f"GrounderJudge: score={score} approval={approval}"],
    }
