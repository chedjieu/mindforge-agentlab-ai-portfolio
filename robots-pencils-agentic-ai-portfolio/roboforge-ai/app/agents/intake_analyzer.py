"""Intake analyzer worker."""

from __future__ import annotations

import json
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.guardrails import check_pack_guardrail
from app.llm import get_chat_model, invoke_with_throttle_fallback
from app.state import Domain, ForgeState


class IntakeOut(BaseModel):
    domain: Literal["modernize", "agentic", "rag", "migration"]
    objectives: list[str] = Field(default_factory=list)
    stakeholders: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    summary: str = ""


def _text(pack: dict) -> str:
    return "\n".join(
        str(pack.get(k) or "")
        for k in ("title", "body", "description", "constraints", "documents")
    )


def intake_analyzer_node(state: ForgeState) -> dict:
    text = _text(state["raw_pack"])
    refusal = check_pack_guardrail(text)
    if refusal:
        return {
            "approval": "rejected",
            "intake": None,
            "step_log": state["step_log"] + [f"GUARDRAIL_REFUSAL: {refusal}"],
        }

    def _call() -> IntakeOut:
        return get_chat_model().with_structured_output(IntakeOut).invoke(
            [
                SystemMessage(
                    content=(
                        "You are the RoboForge intake analyzer. Extract objectives, "
                        "stakeholders, constraints, risks, and domain "
                        "(modernize|agentic|rag|migration)."
                    )
                ),
                HumanMessage(content=text or json.dumps(state["raw_pack"])),
            ]
        )

    try:
        out = invoke_with_throttle_fallback(_call)
        intake = out.model_dump()
        domain: Domain = out.domain  # type: ignore[assignment]
    except Exception:
        domain = "agentic"
        intake = {
            "domain": domain,
            "objectives": ["Production Bedrock agents"],
            "stakeholders": ["Delivery", "Security"],
            "constraints": ["HITL required"],
            "risks": ["Unknown estate"],
            "summary": "Fallback intake",
        }

    return {
        "intake": intake,
        "domain": domain,
        "step_log": state["step_log"] + [f"intake_analyzer: domain={domain}"],
    }
