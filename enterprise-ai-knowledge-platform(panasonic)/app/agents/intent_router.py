"""Intent router — structured domain/intent/sensitivity classification."""

from __future__ import annotations

import os
import re
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app._fake_llm import is_fake_chat_model
from app.guardrails import check_query_guardrail
from app.llm import get_chat_model, invoke_with_throttle_fallback
from app.state import Domain, Intent, KnowledgeState, Sensitivity

DOMAINS: tuple[Domain, ...] = (
    "engineering",
    "manufacturing",
    "hr",
    "support",
    "operations",
)
INTENTS: tuple[Intent, ...] = (
    "factoid",
    "procedure",
    "policy",
    "troubleshooting",
    "relationship",
    "unknown",
)

PII_MARKERS = (
    "ssn",
    "social security",
    "salary",
    "compensation",
    "passport",
    "date of birth",
    "dob",
)


class IntentOutput(BaseModel):
    domain: Literal["engineering", "manufacturing", "hr", "support", "operations"]
    intent: Literal[
        "factoid",
        "procedure",
        "policy",
        "troubleshooting",
        "relationship",
        "unknown",
    ]
    sensitivity: Literal["normal", "sensitive"]
    needs_graph: bool
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str


SYSTEM = (
    "You are an enterprise knowledge intent classifier for Panasonic EGKP. "
    "Classify the user query into exactly one domain "
    "(engineering, manufacturing, hr, support, operations) and one intent "
    "(factoid, procedure, policy, troubleshooting, relationship, unknown). "
    "Set sensitivity=sensitive for HR topics or PII-like requests. "
    "Set needs_graph=true for supersession, applicability, governance, or "
    "multi-hop entity relationship questions. Be conservative on sensitive."
)


def _heuristic(query: str) -> IntentOutput:
    q = (query or "").lower()
    domain: Domain = "support"
    intent: Intent = "unknown"
    needs_graph = False
    sensitivity: Sensitivity = "normal"

    if any(t in q for t in ("pto", "leave", "hr ", "payroll", "remote work", "parental")):
        domain, intent, sensitivity = "hr", "policy", "sensitive"
    elif any(t in q for t in ("torque", "sop", "plant", "assembly", "pn-")):
        domain, intent = "manufacturing", "procedure"
    elif any(t in q for t in ("standard", "connector", "emc", "thermal", "spec")):
        domain, intent = "engineering", "factoid"
    elif any(t in q for t in ("led", "blink", "troubleshoot", "rma", "warranty", "firmware")):
        domain, intent = "support", "troubleshooting"
    elif any(t in q for t in ("runbook", "sev1", "change window", "payment-service", "kafka")):
        domain, intent = "operations", "procedure"

    if any(t in q for t in ("supersed", "which sop", "applies to", "related to", "govern")):
        needs_graph = True
        intent = "relationship"
    if re.search(r"\b(?:pn|sop|std|pol)-\w+", q):
        needs_graph = True

    if domain == "hr" or any(m in q for m in PII_MARKERS):
        sensitivity = "sensitive"

    return IntentOutput(
        domain=domain,
        intent=intent,
        sensitivity=sensitivity,
        needs_graph=needs_graph,
        confidence=0.75,
        rationale="heuristic intent_router (fake/offline)",
    )


def _validate(out: IntentOutput) -> IntentOutput:
    domain = out.domain if out.domain in DOMAINS else "support"
    intent = out.intent if out.intent in INTENTS else "unknown"
    sensitivity = out.sensitivity if out.sensitivity in ("normal", "sensitive") else "normal"
    if domain != out.domain or intent != out.intent:
        return IntentOutput(
            domain="support",  # type: ignore[arg-type]
            intent="unknown",  # type: ignore[arg-type]
            sensitivity="normal",
            needs_graph=bool(out.needs_graph),
            confidence=min(float(out.confidence), 0.4),
            rationale=f"validation fallback ({out.rationale})",
        )
    return IntentOutput(
        domain=domain,  # type: ignore[arg-type]
        intent=intent,  # type: ignore[arg-type]
        sensitivity=sensitivity,  # type: ignore[arg-type]
        needs_graph=bool(out.needs_graph),
        confidence=float(out.confidence),
        rationale=out.rationale,
    )


def intent_router_node(state: KnowledgeState) -> dict:
    refusal = check_query_guardrail(state.get("query", ""))
    if refusal:
        return {
            "intent": "unknown",
            "domain": state.get("domain") or "support",
            "needs_graph": False,
            "sensitivity": "normal",
            "approval": "rejected",
            "draft_answer": {"answer": refusal, "confidence": 0.0},
            "step_log": state["step_log"] + [f"GUARDRAIL_REFUSAL: {refusal[:120]}"],
        }

    query = state.get("query") or ""
    model_name = (os.getenv("EGKP_MODEL") or "").strip()
    if not model_name or is_fake_chat_model(model_name):
        out = _validate(_heuristic(query))
    else:
        def _call() -> IntentOutput:
            llm = get_chat_model().with_structured_output(IntentOutput)
            return llm.invoke(
                [
                    SystemMessage(content=SYSTEM),
                    HumanMessage(
                        content=(
                            f"Role: {state.get('role')}\n"
                            f"Query: {query}"
                        )
                    ),
                ]
            )

        try:
            out = _validate(invoke_with_throttle_fallback(_call))
        except Exception:
            out = _validate(_heuristic(query))

    return {
        "domain": out.domain,
        "intent": out.intent,
        "needs_graph": out.needs_graph,
        "sensitivity": out.sensitivity,
        "step_log": state["step_log"]
        + [
            "intent_router: "
            f"domain={out.domain} intent={out.intent} "
            f"sensitive={out.sensitivity} needs_graph={out.needs_graph} "
            f"conf={out.confidence:.2f}"
        ],
    }
