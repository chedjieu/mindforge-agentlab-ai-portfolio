"""Vertical router — classify engagement brief into vertical + sensitivity."""

from __future__ import annotations

import json
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.guardrails import check_brief_guardrail
from app.llm import get_chat_model, invoke_with_throttle_fallback
from app.state import EngagementState, Sensitivity, Vertical


class RouterOutput(BaseModel):
    vertical: Literal["edtech", "healthcare", "finserv", "retail"]
    sensitivity: Literal["normal", "sensitive", "regulated"]
    policy_pack_id: str
    rationale: str = ""


def _brief_text(raw: dict) -> str:
    parts = [
        str(raw.get("title") or raw.get("subject") or ""),
        str(raw.get("body") or raw.get("description") or ""),
        str(raw.get("constraints") or ""),
    ]
    return "\n".join(p for p in parts if p).strip()


def _heuristic(text: str) -> RouterOutput:
    low = text.lower()
    if any(k in low for k in ("student", "ferpa", "sis", "canvas", "edtech", "enrollment")):
        return RouterOutput(
            vertical="edtech",
            sensitivity="sensitive",
            policy_pack_id="edtech-v1",
            rationale="EdTech/FERPA keywords",
        )
    if any(k in low for k in ("hipaa", "patient", "fhir", "phi", "clinical", "healthcare")):
        return RouterOutput(
            vertical="healthcare",
            sensitivity="regulated",
            policy_pack_id="healthcare-v1",
            rationale="Healthcare/HIPAA keywords",
        )
    if any(k in low for k in ("glba", "bank", "fintech", "soc2", "finserv", "account")):
        return RouterOutput(
            vertical="finserv",
            sensitivity="regulated",
            policy_pack_id="finserv-v1",
            rationale="FinServ keywords",
        )
    if any(k in low for k in ("retail", "merchant", "sku", "personalization")):
        return RouterOutput(
            vertical="retail",
            sensitivity="normal",
            policy_pack_id="retail-v1",
            rationale="Retail keywords",
        )
    return RouterOutput(
        vertical="edtech",
        sensitivity="sensitive",
        policy_pack_id="edtech-v1",
        rationale="Default edtech",
    )


def vertical_router_node(state: EngagementState) -> dict:
    text = _brief_text(state["raw_brief"])
    refusal = check_brief_guardrail(text)
    if refusal:
        return {
            "approval": "rejected",
            "vertical": None,
            "step_log": state["step_log"] + [f"GUARDRAIL_REFUSAL: {refusal}"],
        }

    def _call() -> RouterOutput:
        model = get_chat_model()
        structured = model.with_structured_output(RouterOutput)
        return structured.invoke(
            [
                SystemMessage(
                    content=(
                        "You are the vertical router for R&P Agentic Fabric. "
                        "Classify the engagement brief into edtech, healthcare, finserv, or retail. "
                        "Set sensitivity regulated for healthcare/finserv, sensitive for edtech, "
                        "normal for retail. policy_pack_id must be {vertical}-v1."
                    )
                ),
                HumanMessage(content=text or json.dumps(state["raw_brief"])),
            ]
        )

    try:
        out = invoke_with_throttle_fallback(_call)
    except Exception:
        out = _heuristic(text)

    vertical: Vertical = out.vertical  # type: ignore[assignment]
    sensitivity: Sensitivity = out.sensitivity  # type: ignore[assignment]
    return {
        "vertical": vertical,
        "sensitivity": sensitivity,
        "policy_pack_id": out.policy_pack_id or f"{vertical}-v1",
        "step_log": state["step_log"]
        + [f"vertical_router: {vertical} / {sensitivity} / {out.policy_pack_id}"],
    }
