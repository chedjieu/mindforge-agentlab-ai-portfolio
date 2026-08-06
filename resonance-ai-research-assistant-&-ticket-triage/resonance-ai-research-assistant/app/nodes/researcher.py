"""Researcher node — gathers evidence for each sub-question."""

from __future__ import annotations

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from app.graph import ResearchState
from app.llm import get_chat_model, invoke_with_throttle_fallback
from app.tools.fetch_url import fetch_url
from app.tools.search_local_docs import search_local_docs
from app.tools.summarize import summarize
from app.tools.web_search import web_search

RESEARCHER_SYSTEM = (
    "You are a focused researcher. Use tools to find 1-3 supporting facts with real "
    "source URLs for the given sub-question. When you have enough, reply with a JSON "
    "list of findings."
)

TOOLS = [web_search, fetch_url, search_local_docs, summarize]
TOOL_BY_NAME = {t.name: t for t in TOOLS}
MAX_TOOL_CALLS_PER_SUB = 4
URL_RE = re.compile(r"https?://[^\s\"'\)\]]+")


def _tool_result_str(result: object) -> str:
    if isinstance(result, str):
        return result
    return json.dumps(result, ensure_ascii=False)


def _extract_urls(content: str) -> set[str]:
    urls = set(URL_RE.findall(content))
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return urls
    items = data if isinstance(data, list) else [data]
    for item in items:
        if isinstance(item, dict):
            for key in ("url", "source_url"):
                if item.get(key):
                    urls.add(str(item[key]))
    return urls


def _collect_allowed_urls(messages: list) -> set[str]:
    allowed: set[str] = set()
    for msg in messages:
        if isinstance(msg, ToolMessage):
            allowed.update(_extract_urls(_tool_result_str(msg.content)))
    return allowed


def _parse_findings_json(content: str) -> list[dict]:
    text = content.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    data = json.loads(text)
    if isinstance(data, dict) and "findings" in data:
        data = data["findings"]
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def _validate_findings(
    raw: list[dict], sub_index: int, allowed_urls: set[str]
) -> list[dict]:
    findings: list[dict] = []
    for item in raw:
        url = str(item.get("evidence_url", "")).strip()
        if not url or url not in allowed_urls:
            continue
        findings.append(
            {
                "sub_question_index": sub_index,
                "claim": str(item.get("claim", "")),
                "evidence_url": url,
                "evidence_text": str(item.get("evidence_text", "")),
            }
        )
    return findings


def _format_tool_log(sub_index: int, n_subs: int, name: str, args: dict) -> str:
    preview = args.get("query") or args.get("url") or args.get("text") or args
    return f"[sub {sub_index + 1}/{n_subs}] {name}({preview!r})"


def _research_sub_question(
    sub_q: dict,
    sub_index: int,
    n_subs: int,
    step_log: list[str],
) -> tuple[list[dict], list[str]]:
    messages = [
        SystemMessage(content=RESEARCHER_SYSTEM),
        HumanMessage(content=sub_q.get("text", "")),
    ]
    tool_calls_used = 0

    while True:
        def invoke_llm():
            llm = get_chat_model().bind_tools(TOOLS)
            return llm.invoke(messages)

        ai_msg = invoke_with_throttle_fallback(invoke_llm)
        if not ai_msg.tool_calls:
            allowed_urls = _collect_allowed_urls(messages)
            content = ai_msg.content if isinstance(ai_msg.content, str) else str(ai_msg.content)
            try:
                raw = _parse_findings_json(content)
            except (json.JSONDecodeError, TypeError):
                step_log.append(f"[sub {sub_index + 1}/{n_subs}] failed to parse findings JSON")
                return [], step_log
            findings = _validate_findings(raw, sub_index, allowed_urls)
            if raw and not findings:
                step_log.append(
                    f"[sub {sub_index + 1}/{n_subs}] dropped findings (URL validation failed)"
                )
            return findings, step_log

        if tool_calls_used >= MAX_TOOL_CALLS_PER_SUB:
            step_log.append(f"[sub {sub_index + 1}/{n_subs}] max tool calls reached")
            return [], step_log

        messages.append(ai_msg)
        for tc in ai_msg.tool_calls:
            if tool_calls_used >= MAX_TOOL_CALLS_PER_SUB:
                break
            name = tc["name"]
            args = tc["args"]
            result = TOOL_BY_NAME[name].invoke(args)
            messages.append(
                ToolMessage(
                    content=_tool_result_str(result),
                    tool_call_id=tc["id"],
                    name=name,
                )
            )
            tool_calls_used += 1
            step_log.append(_format_tool_log(sub_index, n_subs, name, args))


def researcher_node(state: ResearchState) -> dict:
    sub_questions = state["sub_questions"]
    step_log = list(state["step_log"])
    all_findings: list[dict] = []
    n_subs = len(sub_questions)

    for i, sub_q in enumerate(sub_questions):
        findings, step_log = _research_sub_question(sub_q, i, n_subs, step_log)
        all_findings.extend(findings)

    return {"findings": all_findings, "step_log": step_log}
