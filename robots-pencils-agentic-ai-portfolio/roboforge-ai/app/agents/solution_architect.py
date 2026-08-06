"""Solution architect — blueprint with three memory layers."""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.llm import get_chat_model, invoke_with_throttle_fallback
from app.memory.episodic import recall_similar
from app.memory.procedural import get_architect_prompt
from app.memory.semantic import recall_org
from app.state import ForgeState


class BlueprintOut(BaseModel):
    title: str
    summary: str
    architecture: list[str] = Field(default_factory=list)
    rag_design: list[str] = Field(default_factory=list)
    agent_topology: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


def solution_architect_node(state: ForgeState) -> dict:
    domain = state.get("domain") or "agentic"
    procedural = get_architect_prompt(domain)
    episodic = recall_similar(state["client_id"], domain, str(state["raw_pack"]))
    semantic = recall_org(state["client_id"])

    def _call() -> BlueprintOut:
        return get_chat_model().with_structured_output(BlueprintOut).invoke(
            [
                SystemMessage(
                    content=(
                        "You are the RoboForge solution architect. Draft a Bedrock/AgentCore "
                        f"blueprint. Cite evidence ids. Style:\n{procedural}"
                    )
                ),
                HumanMessage(
                    content=(
                        f"Pack: {json.dumps(state['raw_pack'])[:2000]}\n"
                        f"Intake: {json.dumps(state.get('intake'))[:1000]}\n"
                        f"Estate: {json.dumps(state.get('estate'))[:1000]}\n"
                        f"Security: {json.dumps(state.get('security_findings'))[:1000]}\n"
                        f"Episodic: {json.dumps(episodic)[:800]}\n"
                        f"Semantic: {json.dumps(semantic)[:500]}\n"
                        f"Evidence: {json.dumps(state.get('evidence'))[:3000]}"
                    )
                ),
            ]
        )

    try:
        bp = invoke_with_throttle_fallback(_call).model_dump()
    except Exception:
        bp = {
            "title": f"{domain.title()} Bedrock blueprint",
            "summary": "AgentCore supervisor with hybrid RAG and HITL.",
            "architecture": ["Bedrock AgentCore", "Neo4j GraphRAG", "HITL console"],
            "rag_design": ["hybrid", "citations"],
            "agent_topology": ["supervisor", "workers", "judges", "hitl"],
            "citations": [e.get("id") for e in (state.get("evidence") or [])[:3]],
            "risk_flags": [],
        }

    return {
        "blueprint": bp,
        "step_log": state["step_log"] + [f"solution_architect: {bp.get('title')}"],
    }
