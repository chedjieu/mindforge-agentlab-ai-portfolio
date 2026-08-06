"""Planner node — decomposes the user question into sub-questions."""

from __future__ import annotations

from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from app.graph import ResearchState
from app.llm import get_chat_model, invoke_with_throttle_fallback

SYSTEM_PROMPT = (
    "You are a research planner. Decompose the user's question into 3-7 sub-questions "
    "that, taken together, fully cover the question. "
    "Each sub-question must explicitly name the specific entity, acronym, product, "
    "regulation, or technical concept it investigates (e.g. 'OpenAI', 'GDPR', "
    "'dynamic resource allocation'). "
    "For comparison questions, include at least one sub-question per side. "
    "For version-specific questions (e.g. Kubernetes 1.30), include sub-questions "
    "about the headline changes in that release. "
    "Tag each as 'web' (current/news/general), 'local' (likely in our internal docs corpus), "
    "or 'both'. Output strict JSON."
)


class SubQuestion(BaseModel):
    text: str
    source: Literal["web", "local", "both"]


class PlannerOutput(BaseModel):
    sub_questions: list[SubQuestion]


def planner_node(state: ResearchState) -> dict:
    memories = state.get("memories") or []
    memory_block = ""
    if memories:
        mem_lines = [m.get("value", {}).get("content", str(m)) for m in memories if m]
        if mem_lines:
            memory_block = "\n\nMemories about this user:\n" + "\n".join(f"- {line}" for line in mem_lines)

    system_content = SYSTEM_PROMPT + memory_block

    def run_planner() -> PlannerOutput:
        llm = get_chat_model().with_structured_output(PlannerOutput)
        return llm.invoke(
            [
                SystemMessage(content=system_content),
                HumanMessage(content=state["question"]),
            ]
        )

    result = invoke_with_throttle_fallback(run_planner)
    return {
        "sub_questions": [sq.model_dump() for sq in result.sub_questions],
        "step_log": state["step_log"] + [f"Planner: {len(result.sub_questions)} sub-questions"],
    }
