"""Summarize long text with an LLM."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from app.llm import get_chat_model


@tool
def summarize(text: str, focus: str = "") -> str:
    """Summarize long text in exactly three sentences. Use this when fetched page content is too long to answer directly."""
    llm = get_chat_model()
    focus_line = f" Emphasise this focus throughout: {focus}." if focus else ""
    messages = [
        SystemMessage(content=f"Summarize the following text in exactly 3 sentences.{focus_line}"),
        HumanMessage(content=text),
    ]
    response = llm.invoke(messages)
    content = response.content
    return content if isinstance(content, str) else str(content)


if __name__ == "__main__":
    sample = (
        "LangGraph is a library for building stateful, multi-actor applications with LLMs. "
        "It extends LangChain with durable execution and human-in-the-loop patterns. "
        "Teams use it for agents that need checkpoints, retries, and long-running workflows."
    )
    print(summarize.invoke({"text": sample, "focus": "LangGraph"}))
