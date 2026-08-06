"""Recommender — structured fraud recommendation + evidence pack."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.guardrails import check_escalate_patterns
from app.llm import get_chat_model, invoke_with_throttle_fallback, is_fake_chat_model
from app.state import InvestigationState


class RecommendationOut(BaseModel):
    action: Literal["clear", "monitor", "escalate", "file_sar", "block"] = "escalate"
    summary: str = ""
    confidence: float = 0.5
    reasoning: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    regulatory_refs: list[str] = Field(default_factory=list)


ALWAYS_HITL = {"wire", "sanctions", "aml", "mule"}


def _build_heuristic(state: InvestigationState) -> RecommendationOut:
    band = state.get("risk_band") or "medium"
    score = float(state.get("risk_score") or 0.0)
    fraud_types = list(state.get("fraud_types") or [])
    evidence = state.get("evidence") or []
    citations = state.get("reg_citations") or []
    graph_paths = state.get("graph_paths") or []
    similar = state.get("similar_cases") or []

    if score >= 0.85 or "sanctions" in fraud_types:
        action = "file_sar"
    elif score >= 0.65:
        action = "escalate"
    elif score >= 0.4:
        action = "monitor"
    else:
        action = "clear"

    eids = [e.get("id") for e in evidence if e.get("id")]
    refs = [
        str(c.get("metadata", {}).get("title") or c.get("id"))
        for c in citations
        if c.get("id") not in (None, "EMPTY")
    ][:5]

    graph_expl = "; ".join(
        p.get("explanation") or "" for p in graph_paths[:3] if p.get("explanation")
    )
    similar_ids = [s.get("id") for s in similar if s.get("id")]

    summary = (
        f"Risk {band} ({score:.2f}) for types={fraud_types}. "
        f"Recommended action: {action}."
    )
    reasoning = (
        f"Fused transaction, identity, graph, and regulatory signals. "
        f"Graph: {graph_expl or 'n/a'}. Similar cases: {similar_ids}."
    )
    return RecommendationOut(
        action=action,  # type: ignore[arg-type]
        summary=summary,
        confidence=min(0.95, 0.55 + score * 0.4),
        reasoning=reasoning,
        evidence_ids=[str(x) for x in eids],
        regulatory_refs=[str(x) for x in refs],
    )


def recommender_node(state: InvestigationState) -> dict:
    from app.llm import _resolved_chat_name

    if is_fake_chat_model(_resolved_chat_name(None)):
        out = _build_heuristic(state)
    else:
        try:
            llm = get_chat_model().with_structured_output(RecommendationOut)
            payload = {
                "risk_score": state.get("risk_score"),
                "risk_band": state.get("risk_band"),
                "fraud_types": state.get("fraud_types"),
                "evidence": state.get("evidence"),
                "graph_paths": state.get("graph_paths"),
                "reg_citations": [
                    {"id": c.get("id"), "text": (c.get("text") or "")[:400]}
                    for c in (state.get("reg_citations") or [])[:5]
                ],
                "similar_cases": [
                    {"id": c.get("id"), "text": (c.get("text") or "")[:300]}
                    for c in (state.get("similar_cases") or [])[:3]
                ],
            }

            def _call():
                return llm.invoke(
                    [
                        {
                            "role": "user",
                            "content": (
                                "Produce an explainable fraud investigation recommendation. "
                                "Do not invent evidence IDs. Use only provided materials.\n"
                                f"{payload}"
                            ),
                        }
                    ]
                )

            raw = invoke_with_throttle_fallback(_call)
            out = raw if isinstance(raw, RecommendationOut) else _build_heuristic(state)
        except Exception:
            out = _build_heuristic(state)

    escalate_hits = check_escalate_patterns(state.get("query") or "")
    fraud_types = set(state.get("fraud_types") or [])
    band = state.get("risk_band") or "medium"
    force_hitl = (
        band in ("high", "critical")
        or bool(fraud_types & ALWAYS_HITL)
        or state.get("sensitivity") == "sensitive"
        or out.confidence < 0.6
        or bool(escalate_hits)
        or out.action in ("escalate", "file_sar", "block")
    )
    approval = "pending" if force_hitl else "auto"

    recommendation = {
        "action": out.action,
        "summary": out.summary,
        "confidence": out.confidence,
        "reasoning": out.reasoning,
        "evidence_ids": out.evidence_ids,
        "regulatory_refs": out.regulatory_refs,
        "graph_explanation": [
            p.get("explanation") for p in (state.get("graph_paths") or [])[:5]
        ],
        "similar_case_ids": [c.get("id") for c in (state.get("similar_cases") or [])[:5]],
        "risk_score": state.get("risk_score"),
        "risk_band": state.get("risk_band"),
        "fraud_types": list(state.get("fraud_types") or []),
        "escalate_flags": escalate_hits,
    }

    return {
        "recommendation": recommendation,
        "approval": approval,
        "step_log": state["step_log"]
        + [f"Recommender: action={out.action} approval={approval} conf={out.confidence}"],
    }
