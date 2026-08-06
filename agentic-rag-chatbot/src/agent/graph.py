"""LangChain tool-calling agent for the knowledge assistant."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI

from src.agent.tools import get_agent_tools, get_turn_sources, reset_turn_state
from src.config import Settings, get_settings
from src.rag.vectorstore import collection_count

SYSTEM_PROMPT = """You are an AI Research Knowledge Assistant grounded in Lilian Weng's blog posts.

Behavior rules:
1. For research questions about ML/LLMs/agents/diffusion/prompting/transformers/etc.,
   ALWAYS call `search_knowledge_base_tool` first before answering.
2. Prefer knowledge-base evidence. Cite sources by title and URL in your final answer.
3. If KB results are weak or empty, you may call `web_search`, then clearly label
   which parts come from the web vs the knowledge base.
4. Use `get_source_summary` when you need to confirm a citation or summarize a specific post.
5. If you still lack evidence, say you do not know. Do not invent paper details or quotes.
6. Keep answers clear and structured. Include a short "Sources" section when KB was used.
"""


def build_llm(settings: Settings | None = None) -> ChatOpenAI:
    settings = settings or get_settings()
    if not settings.openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return ChatOpenAI(
        model=settings.openai_chat_model,
        temperature=0.2,
        api_key=settings.openai_api_key,
    )


def _extract_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "".join(parts)
    return str(content)


def run_agent(message: str, *, settings: Settings | None = None) -> dict[str, Any]:
    """Run one agent turn and return answer, sources, and tool steps."""
    settings = settings or get_settings()
    reset_turn_state()

    count = collection_count(settings)
    if count == 0:
        return {
            "answer": (
                "The knowledge base is empty. Run ingestion first "
                "(`python -m src.ingest` or POST /ingest), then try again."
            ),
            "sources": [],
            "steps": [],
            "error": "empty_knowledge_base",
        }

    tools = get_agent_tools()
    tools_by_name = {t.name: t for t in tools}
    llm = build_llm(settings).bind_tools(tools)

    messages: list = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=message),
    ]
    steps: list[dict[str, Any]] = []
    max_iterations = 6

    for _ in range(max_iterations):
        response = llm.invoke(messages)
        messages.append(response)

        tool_calls = getattr(response, "tool_calls", None) or []
        if not tool_calls:
            answer = _extract_text(response.content).strip()
            return {
                "answer": answer or "I could not generate a response.",
                "sources": get_turn_sources(),
                "steps": steps,
            }

        for call in tool_calls:
            name = call.get("name")
            args = call.get("args") or {}
            call_id = call.get("id") or name
            tool = tools_by_name.get(name)
            if tool is None:
                observation = f"Unknown tool: {name}"
            else:
                try:
                    observation = tool.invoke(args)
                except Exception as exc:  # noqa: BLE001
                    observation = f"Tool error: {exc}"

            steps.append(
                {
                    "tool": name,
                    "input": args,
                    "output_preview": str(observation)[:500],
                }
            )
            messages.append(
                ToolMessage(content=str(observation), tool_call_id=call_id)
            )

    # Fallback if the model never stops calling tools
    final = llm.invoke(
        messages
        + [
            HumanMessage(
                content=(
                    "Please provide your final answer now based on the tool results. "
                    "Do not call more tools."
                )
            )
        ]
    )
    if isinstance(final, AIMessage):
        answer = _extract_text(final.content).strip()
    else:
        answer = _extract_text(final).strip()

    return {
        "answer": answer or "I could not generate a final answer.",
        "sources": get_turn_sources(),
        "steps": steps,
    }
