"""Intent router — advice / fraud / support / mixed."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.guardrails import check_query_guardrail
from app.llm import _resolved_chat_name, get_chat_model, invoke_with_throttle_fallback
from app._fake_llm import is_fake_chat_model
from app.state import SessionState


class IntentOut(BaseModel):
    intent: Literal["advice", "fraud", "support", "mixed", "unknown"] = "unknown"
    needs_graph: bool = False
    needs_rag: bool = True
    run_advisor: bool = False
    run_fraud: bool = False
    run_support: bool = False
    confidence: float = 0.5
    rationale: str = ""


def _heuristic(query: str, alert: dict) -> IntentOut:
    text = f"{query} {alert.get('description', '')}".lower()
    advice_kw = ("invest", "portfolio", "retire", "goal", "risk tolerance", "advise", "save")
    fraud_kw = ("fraud", "suspicious", "wire", "unauthorized", "takeover", "mule", "ofac")
    support_kw = ("balance", "password", "reset", "how do i", "fee", "statement", "help")

    is_advice = any(k in text for k in advice_kw)
    is_fraud = any(k in text for k in fraud_kw) or bool(alert)
    is_support = any(k in text for k in support_kw)

    if alert and not is_advice and not is_support:
        is_fraud = True
    if is_advice and is_fraud:
        intent = "mixed"
    elif is_advice:
        intent = "advice"
    elif is_fraud:
        intent = "fraud"
    elif is_support:
        intent = "support"
    else:
        intent = "support"

    return IntentOut(
        intent=intent,  # type: ignore[arg-type]
        needs_graph=intent in ("fraud", "mixed", "advice"),
        needs_rag=True,
        run_advisor=intent in ("advice", "mixed"),
        run_fraud=intent in ("fraud", "mixed") or bool(alert),
        run_support=intent in ("support", "mixed") or intent == "unknown",
        confidence=0.85,
        rationale="heuristic intent classification",
    )


def intent_router_node(state: SessionState) -> dict:
    query = state.get("query") or ""
    alert = state.get("txn_alert") or {}
    blocked = check_query_guardrail(query)
    if blocked:
        return {
            "intent": "unknown",
            "needs_graph": False,
            "needs_rag": False,
            "run_advisor": False,
            "run_fraud": False,
            "run_support": False,
            "approval": "rejected",
            "retrieved_chunks": [{"id": "guardrail", "text": blocked}],
            "graph_paths": [{"nodes": [], "explanation": "skipped"}],
            "advice_draft": {"skipped": True},
            "fraud_finding": {"skipped": True},
            "support_answer": {"summary": blocked, "citations": []},
            "compliance_score": 1.0,
            "risk_score": 0.0,
            "risk_band": "low",
            "final_response": {
                "summary": blocked,
                "kind": "blocked",
                "citations": [],
                "reasoning": "GUARDRAIL_REFUSAL",
            },
            "grounding_score": 1.0,
            "step_log": state["step_log"] + ["Intent: GUARDRAIL_REFUSAL"],
        }

    if is_fake_chat_model(_resolved_chat_name(None)):
        out = _heuristic(query, alert)
    else:
        try:
            llm = get_chat_model().with_structured_output(IntentOut)

            def _call():
                return llm.invoke(
                    [
                        {
                            "role": "user",
                            "content": f"Classify banking request.\nQuery: {query}\nAlert: {alert}",
                        }
                    ]
                )

            raw = invoke_with_throttle_fallback(_call)
            out = raw if isinstance(raw, IntentOut) else _heuristic(query, alert)
        except Exception:
            out = _heuristic(query, alert)

    # Ensure at least one specialist runs
    if not (out.run_advisor or out.run_fraud or out.run_support):
        out.run_support = True

    return {
        "intent": out.intent,
        "needs_graph": out.needs_graph,
        "needs_rag": out.needs_rag,
        "run_advisor": out.run_advisor,
        "run_fraud": out.run_fraud,
        "run_support": out.run_support,
        "step_log": state["step_log"]
        + [
            f"Intent: {out.intent} advisor={out.run_advisor} fraud={out.run_fraud} "
            f"support={out.run_support}"
        ],
    }
