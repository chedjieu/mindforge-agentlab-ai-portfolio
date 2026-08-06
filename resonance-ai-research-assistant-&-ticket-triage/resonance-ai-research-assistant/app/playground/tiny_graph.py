"""15-line LangGraph demo — Session 3."""

from __future__ import annotations

import os
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class S(TypedDict):
    q: str
    a: str


def respond(state: S) -> dict:
    return {"a": f"You asked: {state['q']}"}


app = StateGraph(S)
app.add_node("respond", respond)
app.add_edge(START, "respond")
app.add_edge("respond", END)
graph = app.compile()

if __name__ == "__main__":
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    result = graph.invoke({"q": "hello"})
    print(result)
    project = os.getenv("LANGSMITH_PROJECT", "default")
    print(f"LangSmith: https://smith.langchain.com (project={project})")
