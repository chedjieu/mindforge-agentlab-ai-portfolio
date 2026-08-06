from __future__ import annotations

from typing import Any, Iterator

from langgraph.graph import END, StateGraph

from app.agents.nodes import (
    answer_node,
    research_node,
    supervisor_node,
    tools_node,
    writer_node,
)
from app.agents.state import AgentState
from app.memory.short_term import get_checkpointer
from app.observability.tracing import traced_span


def _route_after_supervisor(state: AgentState) -> str:
    route = state.get("route") or "answer"
    if route == "research":
        return "research"
    if route == "tools":
        return "tools"
    if route == "writer":
        return "writer"
    if route == "end":
        return "end"
    return "answer"


def _after_research(state: AgentState) -> str:
    message = (state.get("user_message") or "").lower()
    if any(k in message for k in ("study note", "study guide", "markdown", "write notes")):
        return "writer"
    return "answer"


def _after_tools(state: AgentState) -> str:
    return "answer"


def build_graph(checkpointer=None):
    graph = StateGraph(AgentState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("research", research_node)
    graph.add_node("tools", tools_node)
    graph.add_node("writer", writer_node)
    graph.add_node("answer", answer_node)

    graph.set_entry_point("supervisor")
    graph.add_conditional_edges(
        "supervisor",
        _route_after_supervisor,
        {
            "research": "research",
            "tools": "tools",
            "writer": "writer",
            "answer": "answer",
            "end": END,
        },
    )
    graph.add_conditional_edges(
        "research",
        _after_research,
        {"writer": "writer", "answer": "answer"},
    )
    graph.add_conditional_edges(
        "tools",
        _after_tools,
        {"answer": "answer"},
    )
    graph.add_edge("writer", END)
    graph.add_edge("answer", END)

    return graph.compile(checkpointer=checkpointer or get_checkpointer())


_GRAPH = None


def get_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_graph()
    return _GRAPH


def run_agent(message: str, thread_id: str = "default") -> dict[str, Any]:
    with traced_span("agent.run", {"thread_id": thread_id}):
        graph = get_graph()
        config = {"configurable": {"thread_id": thread_id}}
        initial: AgentState = {
            "user_message": message,
            "messages": [{"role": "user", "content": message}],
            "events": [],
            "citations": [],
        }
        result = graph.invoke(initial, config=config)
        return {
            "thread_id": thread_id,
            "answer": result.get("answer") or result.get("draft") or "",
            "route": result.get("route"),
            "citations": result.get("citations") or [],
            "events": result.get("events") or [],
        }


def stream_agent(message: str, thread_id: str = "default") -> Iterator[dict[str, Any]]:
    """Yield node/tool events, answer tokens, then a final payload."""
    with traced_span("agent.stream", {"thread_id": thread_id}):
        graph = get_graph()
        config = {"configurable": {"thread_id": thread_id}}
        initial: AgentState = {
            "user_message": message,
            "messages": [{"role": "user", "content": message}],
            "events": [],
            "citations": [],
        }

        for update in graph.stream(initial, config=config, stream_mode="updates"):
            if not isinstance(update, dict):
                continue
            for node_name, payload in update.items():
                payload = payload or {}
                yield {
                    "type": "node",
                    "node": node_name,
                    "update": {
                        k: payload.get(k)
                        for k in ("route", "tool_name", "citations", "answer")
                        if k in payload
                    },
                }
                for event in payload.get("events") or []:
                    yield {"type": "event", **event}

        state = graph.get_state(config)
        values = state.values if state else {}
        final = {
            "thread_id": thread_id,
            "answer": values.get("answer") or values.get("draft") or "",
            "route": values.get("route"),
            "citations": values.get("citations") or [],
            "events": values.get("events") or [],
        }

        answer = final["answer"]
        chunk_size = 48
        for i in range(0, len(answer), chunk_size):
            yield {"type": "token", "content": answer[i : i + chunk_size]}
        yield {"type": "final", **final}
