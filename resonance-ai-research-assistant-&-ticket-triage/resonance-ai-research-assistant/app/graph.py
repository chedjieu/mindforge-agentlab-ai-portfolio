"""Research assistant LangGraph — recall -> planner -> researcher -> writer -> guard -> extract."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app._warnings import suppress_langchain_deprecation_warnings
from app.guardrails import validate_citations
from app.llm import ensure_chat_model_available, get_chat_model, invoke_with_throttle_fallback
from app.memory import get_store, recall, remember

suppress_langchain_deprecation_warnings()

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph

_graph: CompiledStateGraph | None = None


class ResearchState(TypedDict):
    question: str
    sub_questions: list[dict]
    findings: list[dict]
    report: str
    step_log: list[str]
    memories: list[dict]
    user_id: str


DEFAULT_USER = "default"
MEMORY_NAMESPACE_PREFIX = "research_user"

EXTRACT_SYSTEM = (
    "Looking at the user's question and the report, is there any preference or "
    "stable fact about this user worth remembering for future research sessions? "
    'Return JSON with "worth_remembering": bool and "content": str.'
)


def _user_namespace(state: ResearchState) -> tuple[str, ...]:
    user_id = state.get("user_id") or DEFAULT_USER
    return (MEMORY_NAMESPACE_PREFIX, user_id)


def recall_node(state: ResearchState) -> dict:
    """Pull top-3 memories for the current user before planning."""
    store = get_store()
    ns = _user_namespace(state)
    mems = recall(store, ns, state["question"], k=3)
    return {
        "memories": mems,
        "step_log": state["step_log"] + [f"Recall: {len(mems)} memories loaded"],
    }


def guard_node(state: ResearchState) -> dict:
    allowed_urls = {
        str(f["evidence_url"]) for f in state["findings"] if f.get("evidence_url")
    }
    ok, bad_urls = validate_citations(state["report"], allowed_urls)
    report = state["report"]
    if not ok:
        report = f"> WARNING: invalid citations detected: {bad_urls}\n\n{report}"
    return {
        "report": report,
        "step_log": state["step_log"] + ["Guard: citations validated"],
    }


def extract_node(state: ResearchState) -> dict:
    """Ask the LLM if there's a user preference/fact worth remembering."""
    from langchain_core.messages import HumanMessage, SystemMessage

    payload = json.dumps(
        {"question": state["question"], "report": state["report"][:4000]},
        ensure_ascii=False,
    )

    def run_extract():
        llm = get_chat_model()
        return llm.invoke(
            [
                SystemMessage(content=EXTRACT_SYSTEM),
                HumanMessage(content=payload),
            ]
        )

    ai_msg = invoke_with_throttle_fallback(run_extract)
    content = ai_msg.content if isinstance(ai_msg.content, str) else str(ai_msg.content)

    worth = False
    mem_content = ""
    try:
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        blob = fence.group(1).strip() if fence else content.strip()
        data = json.loads(blob)
        worth = bool(data.get("worth_remembering"))
        mem_content = str(data.get("content", ""))
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    log_msg = "Extract: nothing to remember"
    if worth and mem_content:
        store = get_store()
        ns = _user_namespace(state)
        remember(store, ns, mem_content, kind="fact")
        log_msg = f"Extract: remembered '{mem_content[:60]}'"

    return {"step_log": state["step_log"] + [log_msg]}


async def build_graph() -> CompiledStateGraph:
    """Build and cache the compiled research graph."""
    global _graph
    if _graph is not None:
        return _graph

    from app.nodes.planner import planner_node
    from app.nodes.researcher import researcher_node
    from app.nodes.writer import writer_node

    builder = StateGraph(ResearchState)
    builder.add_node("recall", recall_node)
    builder.add_node("planner", planner_node)
    builder.add_node("researcher", researcher_node)
    builder.add_node("writer", writer_node)
    builder.add_node("guard", guard_node)
    builder.add_node("extract", extract_node)
    builder.add_edge(START, "recall")
    builder.add_edge("recall", "planner")
    builder.add_edge("planner", "researcher")
    builder.add_edge("researcher", "writer")
    builder.add_edge("writer", "guard")
    builder.add_edge("guard", "extract")
    builder.add_edge("extract", END)

    _graph = builder.compile(checkpointer=InMemorySaver())
    return _graph


async def stream_research(question: str, thread_id: str):
    using_fake = ensure_chat_model_available()
    graph = await build_graph()
    step_log: list[str] = []
    if using_fake:
        step_log.append("Warning: cloud model throttled — using offline fake model")

    async for event in graph.astream_events(
        {
            "question": question,
            "sub_questions": [],
            "findings": [],
            "report": "",
            "step_log": step_log,
            "memories": [],
            "user_id": DEFAULT_USER,
        },
        config={"configurable": {"thread_id": thread_id}},
        version="v2",
    ):
        yield event
