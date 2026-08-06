from __future__ import annotations

import json
import re
from typing import Any

import ollama

from app.agents.prompts import (
    ANSWER_SYSTEM,
    RESEARCH_SYSTEM,
    SUPERVISOR_SYSTEM,
    WRITER_SYSTEM,
)
from app.agents.state import AgentState
from app.agents.tools import run_tool
from app.api.schemas import FinalAnswer, ResearchNotes, StudyNote
from app.config import get_settings
from app.guardrails.groundedness import REFUSAL, grounded_or_refuse, is_grounded
from app.memory.long_term import recall
from app.observability.tracing import traced_span
from app.rag.retriever import format_context, retrieve


def _chat(system: str, user: str) -> str:
    settings = get_settings()
    client = ollama.Client(host=settings.ollama_host)
    response = client.chat(
        model=settings.ollama_llm_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return response["message"]["content"]


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def supervisor_node(state: AgentState) -> dict[str, Any]:
    with traced_span("agent.supervisor"):
        message = state["user_message"]
        lowered = message.lower()

        # Deterministic shortcuts for reliability in demos / evals
        if any(k in lowered for k in ("weather", "cardiff", "temperature")):
            route, tool_name = "tools", "get_cardiff_weather"
        elif any(k in lowered for k in ("save study", "write study", "study note", "markdown file")):
            route, tool_name = "tools", "write_study_note"
        elif "remember" in lowered and ("that" in lowered or "fact" in lowered):
            route, tool_name = "tools", "remember_fact"
        elif any(k in lowered for k in ("study notes", "study guide", "comprehensive notes")):
            route, tool_name = "research", None
        else:
            raw = _chat(
                SUPERVISOR_SYSTEM,
                f"User message:\n{message}\n\nPick the next route.",
            )
            try:
                parsed = _extract_json(raw)
                route = parsed.get("route", "research")
                tool_name = parsed.get("tool_name")
            except Exception:
                route, tool_name = "research", None

        if route not in {"research", "tools", "writer", "answer", "end"}:
            route = "research"

        return {
            "route": route,
            "tool_name": tool_name,
            "events": [{"type": "route", "route": route, "tool_name": tool_name}],
        }


def research_node(state: AgentState) -> dict[str, Any]:
    with traced_span("agent.research"):
        question = state["user_message"]
        chunks = retrieve(question)
        memories = recall(question, top_k=3)
        context = format_context(chunks)
        memory_block = "\n".join(f"- {m}" for m in memories) or "(none)"

        if not is_grounded(chunks) and "weather" not in question.lower():
            notes = REFUSAL
            citations: list[str] = []
        else:
            prompt = (
                f"Memories:\n{memory_block}\n\n"
                f"Context:\n{context}\n\n"
                f"Question:\n{question}\n\n"
                "Return JSON with keys facts, open_questions, citations."
            )
            raw = _chat(RESEARCH_SYSTEM, prompt)
            try:
                parsed = _extract_json(raw)
                model = ResearchNotes.model_validate(parsed)
                notes = "\n".join(f"- {fact}" for fact in model.facts) or raw
                citations = model.citations or [c.citation for c in chunks]
            except Exception:
                notes = raw
                citations = [c.citation for c in chunks]

        return {
            "context": context,
            "citations": citations,
            "research_notes": notes,
            "memories": memories,
            "events": [{"type": "research", "citations": citations}],
            "messages": [{"role": "assistant", "content": f"Research notes:\n{notes}"}],
        }


def tools_node(state: AgentState) -> dict[str, Any]:
    with traced_span("agent.tools"):
        tool_name = state.get("tool_name") or "search_pdf"
        message = state["user_message"]
        args: dict[str, Any] = {}

        if tool_name == "search_pdf":
            args = {"question": message}
        elif tool_name == "write_study_note":
            content = state.get("draft") or state.get("research_notes") or message
            args = {"content": content}
        elif tool_name == "remember_fact":
            args = {"content": message}
        elif tool_name == "get_cardiff_weather":
            args = {}

        result = run_tool(tool_name, args)
        return {
            "draft": result,
            "events": [{"type": "tool", "tool_name": tool_name, "result": result[:500]}],
            "messages": [
                {
                    "role": "tool",
                    "content": f"{tool_name}: {result}",
                }
            ],
        }


def writer_node(state: AgentState) -> dict[str, Any]:
    with traced_span("agent.writer"):
        notes = state.get("research_notes") or state.get("draft") or ""
        prompt = (
            f"Research notes:\n{notes}\n\n"
            "Return JSON with keys title, markdown, sections."
        )
        raw = _chat(WRITER_SYSTEM, prompt)
        try:
            parsed = _extract_json(raw)
            model = StudyNote.model_validate(parsed)
            markdown = model.markdown
            title = model.title
        except Exception:
            markdown = raw
            title = "Study Notes"

        # Persist via tool for parity with notebook 2/3
        save_result = run_tool("write_study_note", {"content": markdown})
        return {
            "draft": markdown,
            "answer": markdown,
            "events": [
                {"type": "writer", "title": title},
                {"type": "tool", "tool_name": "write_study_note", "result": save_result},
            ],
            "messages": [{"role": "assistant", "content": markdown}],
        }


def answer_node(state: AgentState) -> dict[str, Any]:
    with traced_span("agent.answer"):
        message = state["user_message"]
        route = state.get("route")
        context = state.get("context") or ""
        draft = state.get("draft") or ""
        notes = state.get("research_notes") or ""
        memories = state.get("memories") or recall(message, top_k=3)

        # If research already refused, surface that
        if notes == REFUSAL:
            answer = REFUSAL
            citations = []
        elif route == "tools" and draft:
            prompt = (
                f"User question: {message}\n\n"
                f"Tool result:\n{draft}\n\n"
                "Write a helpful final answer."
            )
            answer = _chat(ANSWER_SYSTEM, prompt)
            citations = state.get("citations") or []
        elif context:
            chunks = retrieve(message)
            prompt = (
                f"Memories:\n{chr(10).join(memories)}\n\n"
                f"Context:\n{context}\n\n"
                f"Research notes:\n{notes}\n\n"
                f"Question:\n{message}"
            )
            draft_answer = _chat(ANSWER_SYSTEM, prompt)
            answer = grounded_or_refuse(chunks, draft_answer)
            citations = state.get("citations") or [c.citation for c in chunks]
        else:
            answer = _chat(ANSWER_SYSTEM, message)
            citations = state.get("citations") or []

        try:
            FinalAnswer(answer=answer, citations=citations)
        except Exception:
            pass

        return {
            "answer": answer,
            "citations": citations,
            "events": [{"type": "answer", "preview": answer[:200]}],
            "messages": [{"role": "assistant", "content": answer}],
        }
