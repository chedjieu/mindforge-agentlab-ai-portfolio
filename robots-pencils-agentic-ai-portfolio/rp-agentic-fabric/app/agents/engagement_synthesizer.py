"""Engagement synthesizer — draft plan using three memory layers."""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.llm import get_chat_model, invoke_with_throttle_fallback
from app.memory.episodic import recall_similar_engagements
from app.memory.procedural import get_synthesizer_prompt
from app.memory.semantic import recall_tenant
from app.state import EngagementState


class PlanOutput(BaseModel):
    title: str
    summary: str
    architecture: list[str] = Field(default_factory=list)
    playbook_steps: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    recommended_action: str = "publish"


def engagement_synthesizer_node(state: EngagementState, *, store=None) -> dict:
    vertical = state["vertical"] or "edtech"
    procedural = get_synthesizer_prompt(vertical)
    episodic = recall_similar_engagements(
        tenant_id=state["tenant_id"],
        vertical=vertical,
        query=str(state["raw_brief"]),
    )
    semantic = recall_tenant(state["tenant_id"], store=store)

    evidence_blob = json.dumps(state.get("evidence") or [], ensure_ascii=False)[:6000]
    reuse_blob = json.dumps(state.get("reuse_decisions") or [], ensure_ascii=False)[:2000]
    regs = (state.get("guardrail_config") or {}).get("regs") or []

    def _call() -> PlanOutput:
        model = get_chat_model()
        structured = model.with_structured_output(PlanOutput)
        return structured.invoke(
            [
                SystemMessage(
                    content=(
                        "You are the engagement synthesizer for R&P Agentic Fabric. "
                        "Draft an engagement plan / playbook. Cite evidence ids. "
                        "Never invent other tenants' identifiers. "
                        f"Procedural style:\n{procedural}"
                    )
                ),
                HumanMessage(
                    content=(
                        f"Brief: {json.dumps(state['raw_brief'], ensure_ascii=False)}\n"
                        f"Vertical: {vertical}\nRegs: {regs}\n"
                        f"Episodic: {json.dumps(episodic, ensure_ascii=False)[:1500]}\n"
                        f"Semantic: {json.dumps(semantic, ensure_ascii=False)[:800]}\n"
                        f"Reuse: {reuse_blob}\nEvidence: {evidence_blob}"
                    )
                ),
            ]
        )

    try:
        out = invoke_with_throttle_fallback(_call)
        plan = out.model_dump()
    except Exception:
        plan = {
            "title": f"{vertical.title()} engagement plan",
            "summary": f"Tenant-scoped {vertical} delivery pattern under {regs}.",
            "architecture": [
                "LangGraph supervisor",
                "Tenant-scoped RAG + Neo4j",
                "HITL + audit pack",
            ],
            "playbook_steps": [
                "Load policy pack",
                "Sanitize reusable IP",
                "Assemble workers",
                "Judge gate + HITL",
                "Publish audit pack",
            ],
            "citations": [e.get("id") for e in (state.get("evidence") or [])[:3]],
            "risk_flags": [],
            "recommended_action": "escalate"
            if vertical in ("healthcare", "finserv")
            else "publish",
        }

    return {
        "draft_plan": plan,
        "step_log": state["step_log"] + [f"engagement_synthesizer: drafted '{plan.get('title')}'"],
    }
