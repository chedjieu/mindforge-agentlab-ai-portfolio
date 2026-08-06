"""Triage router — classify fraud hypotheses, rail, sensitivity, tool needs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.guardrails import check_query_guardrail
from app.llm import get_chat_model, invoke_with_throttle_fallback, is_fake_chat_model
from app.state import InvestigationState


class TriageOutput(BaseModel):
    fraud_types: list[
        Literal[
            "wire",
            "ach",
            "card",
            "ato",
            "mule",
            "sanctions",
            "aml",
            "app_bec",
            "instant_pay",
            "unknown",
        ]
    ] = Field(default_factory=list)
    payment_rail: Literal["wire", "ach", "card", "rtp", "fednow", "internal", "unknown"] = "unknown"
    sensitivity: Literal["normal", "sensitive"] = "normal"
    needs_graph: bool = False
    needs_identity: bool = True
    confidence: float = 0.5
    rationale: str = ""


ALWAYS_HITL_TYPES = {"wire", "sanctions", "aml", "mule"}


def _heuristic_triage(alert: dict, query: str) -> TriageOutput:
    text = f"{query} {alert.get('description', '')} {alert.get('alert_type', '')}".lower()
    rail = str(alert.get("payment_rail") or alert.get("channel") or "unknown").lower()
    if rail not in ("wire", "ach", "card", "rtp", "fednow", "internal"):
        if "wire" in text:
            rail = "wire"
        elif "ach" in text:
            rail = "ach"
        elif "fednow" in text or "rtp" in text:
            rail = "fednow" if "fednow" in text else "rtp"
        elif "card" in text:
            rail = "card"
        else:
            rail = "unknown"

    types: list[str] = []
    for key in (
        "sanctions",
        "ofac",
        "mule",
        "wire",
        "ach",
        "ato",
        "account takeover",
        "card",
        "app",
        "bec",
        "aml",
        "fednow",
        "rtp",
    ):
        if key in text or key in str(alert.get("alert_type", "")).lower():
            if key in ("ofac",):
                types.append("sanctions")
            elif key == "account takeover":
                types.append("ato")
            elif key in ("app", "bec"):
                types.append("app_bec")
            elif key in ("fednow", "rtp"):
                types.append("instant_pay")
            else:
                types.append(key)  # type: ignore[arg-type]

    hint = alert.get("fraud_types") or alert.get("tags") or []
    for t in hint:
        if t not in types:
            types.append(str(t))

    if not types:
        types = [rail if rail in ("wire", "ach", "card") else "unknown"]

    # Normalize
    norm = []
    for t in types:
        if t in (
            "wire",
            "ach",
            "card",
            "ato",
            "mule",
            "sanctions",
            "aml",
            "app_bec",
            "instant_pay",
            "unknown",
        ):
            if t not in norm:
                norm.append(t)
    if not norm:
        norm = ["unknown"]

    needs_graph = bool(
        set(norm) & {"mule", "wire", "ach", "aml", "sanctions"}
        or alert.get("needs_graph")
        or "shared" in text
    )
    sensitive = bool(set(norm) & ALWAYS_HITL_TYPES) or rail in ("wire",)
    return TriageOutput(
        fraud_types=norm,  # type: ignore[arg-type]
        payment_rail=rail if rail in ("wire", "ach", "card", "rtp", "fednow", "internal", "unknown") else "unknown",  # type: ignore[arg-type]
        sensitivity="sensitive" if sensitive else "normal",
        needs_graph=needs_graph,
        needs_identity=True,
        confidence=0.85,
        rationale="heuristic triage from alert metadata",
    )


def triage_router_node(state: InvestigationState) -> dict:
    query = state.get("query") or ""
    alert = state.get("alert") or {}
    blocked = check_query_guardrail(query) or check_query_guardrail(
        str(alert.get("description") or "")
    )
    if blocked:
        return {
            "fraud_types": ["unknown"],
            "payment_rail": "unknown",
            "sensitivity": "sensitive",
            "needs_graph": False,
            "needs_identity": False,
            "approval": "rejected",
            "recommendation": {
                "action": "reject",
                "summary": blocked,
                "confidence": 1.0,
                "evidence_ids": [],
                "reasoning": "GUARDRAIL_REFUSAL",
            },
            "grounding_score": 1.0,
            "risk_score": 0.0,
            "risk_band": "low",
            "txn_features": {},
            "identity_findings": [{"finding": "blocked"}],
            "reg_citations": [{"id": "guardrail", "text": blocked}],
            "similar_cases": [{"id": "none"}],
            "graph_paths": [{"nodes": [], "explanation": "skipped"}],
            "step_log": state["step_log"] + ["Triage: GUARDRAIL_REFUSAL"],
        }

    model_name = None
    from app.llm import _resolved_chat_name

    if is_fake_chat_model(_resolved_chat_name(model_name)):
        out = _heuristic_triage(alert, query)
    else:
        try:
            llm = get_chat_model().with_structured_output(TriageOutput)

            def _call():
                return llm.invoke(
                    [
                        {
                            "role": "user",
                            "content": (
                                "Classify this bank fraud alert for investigation routing.\n"
                                f"Alert JSON: {alert}\nQuery: {query}"
                            ),
                        }
                    ]
                )

            out = invoke_with_throttle_fallback(_call)
            if not isinstance(out, TriageOutput):
                out = _heuristic_triage(alert, query)
        except Exception:
            out = _heuristic_triage(alert, query)

    entities = {
        "customer_id": alert.get("customer_id"),
        "device_id": alert.get("device_id"),
        "ip": alert.get("ip"),
        "phone": alert.get("phone"),
        "beneficiary": alert.get("beneficiary"),
        "beneficiary_name": alert.get("beneficiary_name"),
        "merchant": alert.get("merchant"),
    }

    return {
        "fraud_types": list(out.fraud_types),
        "payment_rail": out.payment_rail,
        "sensitivity": out.sensitivity,
        "needs_graph": out.needs_graph,
        "needs_identity": out.needs_identity,
        "entities": entities,
        "step_log": state["step_log"]
        + [
            f"Triage: types={list(out.fraud_types)} rail={out.payment_rail} "
            f"graph={out.needs_graph} sens={out.sensitivity}"
        ],
    }
