"""Graph walker — Neo4j / seed JSONL traversal with tool budget ≤ 6."""

from __future__ import annotations

import json
import os
import re

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from app._fake_llm import is_fake_chat_model
from app.llm import get_chat_model, invoke_with_throttle_fallback
from app.state import KnowledgeState
from app.tools.neo4j_graph import (
    extract_entity_candidates,
    lookup_entity,
    lookup_entity_impl,
    traverse_relations,
    traverse_relations_impl,
)

GRAPH_SYSTEM = (
    "You are a knowledge-graph walker for an enterprise knowledge platform. "
    "Extract entities from the user query and the retrieved chunk entity lists. "
    "Use lookup_entity and traverse_relations to explore SUPERSEDES, APPLIES_TO, "
    "GOVERNS, REQUIRES, and LOCATED_AT as needed. "
    "Stop calling tools when you can answer the relationship question. "
    "Budget: 6 tool calls max."
)

SUMMARIZE_SYSTEM = (
    "Summarise graph exploration as a JSON list of objects with keys "
    '"nodes" (list of entity ids), "rels" (list of relationship types), and '
    '"rationale" (short string). Return only the JSON list.'
)

TOOLS = [lookup_entity, traverse_relations]
TOOL_BY_NAME = {t.name: t for t in TOOLS}
MAX_TOOL_CALLS = 6
DEFAULT_RELS = ["SUPERSEDES", "APPLIES_TO", "GOVERNS", "REQUIRES", "LOCATED_AT"]


def _tool_result_str(result: object) -> str:
    if isinstance(result, str):
        return result
    return json.dumps(result, ensure_ascii=False)


def _truncate_args(args: dict, n: int = 80) -> str:
    text = json.dumps(args, ensure_ascii=False)
    return text if len(text) <= n else text[: n - 3] + "..."


def _parse_paths_json(content: str) -> list[dict]:
    text = (content or "").strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    m = re.search(r"\[.*\]", text, flags=re.S)
    if m:
        text = m.group(0)
    data = json.loads(text)
    if not isinstance(data, list):
        return []
    paths: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        nodes = item.get("nodes") or []
        rels = item.get("rels") or []
        if not nodes:
            continue
        paths.append(
            {
                "nodes": list(nodes),
                "rels": list(rels),
                "rationale": str(item.get("rationale", "")),
            }
        )
    return paths


def _heuristic_walk(query: str, chunks: list[dict]) -> list[dict]:
    """Deterministic walk used for fake model / empty LLM tool loops."""
    candidates = extract_entity_candidates(query, chunks)
    paths: list[dict] = []
    seen: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()
    for eid in candidates[:6]:
        ent = lookup_entity_impl(eid)
        if not ent:
            continue
        real_id = str(ent["id"])
        traversed = traverse_relations_impl(real_id, rel_types=DEFAULT_RELS, hops=2)
        for p in traversed:
            key = (tuple(p.get("nodes") or []), tuple(p.get("rels") or []))
            if key in seen:
                continue
            seen.add(key)
            paths.append(
                {
                    "nodes": list(p.get("nodes") or []),
                    "rels": list(p.get("rels") or []),
                    "rationale": str(p.get("rationale") or f"heuristic walk from {real_id}"),
                }
            )
        if len(paths) >= 8:
            break
    return paths


def _paths_from_tool_messages(messages: list) -> list[dict]:
    paths: list[dict] = []
    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue
        try:
            data = json.loads(msg.content if isinstance(msg.content, str) else str(msg.content))
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("nodes"):
                    paths.append(
                        {
                            "nodes": list(item.get("nodes") or []),
                            "rels": list(item.get("rels") or []),
                            "rationale": str(item.get("rationale") or msg.name or "tool"),
                        }
                    )
        elif isinstance(data, dict) and data.get("id"):
            # lookup_entity hit — pair with later traversals; record singleton
            paths.append(
                {
                    "nodes": [data["id"]],
                    "rels": [],
                    "rationale": f"looked up {data['id']}",
                }
            )
    return paths


def graph_walker_node(state: KnowledgeState) -> dict:
    step_log = list(state["step_log"])
    query = state.get("query") or ""
    chunks = state.get("retrieved_chunks") or []

    if not state.get("needs_graph"):
        # Safe if called: return a marker empty path list so supervisor proceeds.
        # (Supervisor only routes here when needs_graph and graph_paths == [].)
        step_log.append("graph_walker: needs_graph=false — skipping walk")
        return {"graph_paths": [{"nodes": [], "rels": [], "rationale": "skipped"}], "step_log": step_log}

    model_name = (os.getenv("EGKP_MODEL") or "").strip()
    use_fake = not model_name or is_fake_chat_model(model_name)

    if use_fake:
        paths = _heuristic_walk(query, chunks)
        step_log.append(f"graph_walker: heuristic paths={len(paths)} (fake/offline)")
        if not paths:
            paths = [{"nodes": [], "rels": [], "rationale": "no graph entities found"}]
        return {"graph_paths": paths, "step_log": step_log}

    candidates = extract_entity_candidates(query, chunks)
    payload = {
        "query": query,
        "domain": state.get("domain"),
        "candidate_entities": candidates,
        "chunk_entities": [
            {
                "doc_id": c.get("doc_id"),
                "entities": (c.get("metadata") or {}).get("entities"),
            }
            for c in chunks[:5]
            if c.get("chunk_id") != "EMPTY"
        ],
    }
    messages: list = [
        SystemMessage(content=GRAPH_SYSTEM),
        HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
    ]
    tool_calls_used = 0

    while tool_calls_used < MAX_TOOL_CALLS:

        def invoke_with_tools():
            llm = get_chat_model().bind_tools(TOOLS)
            return llm.invoke(messages)

        ai_msg = invoke_with_throttle_fallback(invoke_with_tools)
        if not getattr(ai_msg, "tool_calls", None):
            break

        messages.append(ai_msg)
        for tc in ai_msg.tool_calls:
            if tool_calls_used >= MAX_TOOL_CALLS:
                break
            name = tc["name"]
            args = tc.get("args") or {}
            if name not in TOOL_BY_NAME:
                continue
            result = TOOL_BY_NAME[name].invoke(args)
            messages.append(
                ToolMessage(
                    content=_tool_result_str(result),
                    tool_call_id=tc["id"],
                    name=name,
                )
            )
            tool_calls_used += 1
            step_log.append(f"graph_walker: {name}({_truncate_args(args)})")

    if tool_calls_used >= MAX_TOOL_CALLS:
        step_log.append(f"graph_walker: max tool calls ({MAX_TOOL_CALLS}) reached")

    def summarize():
        llm = get_chat_model()
        return llm.invoke(
            [
                SystemMessage(content=SUMMARIZE_SYSTEM),
                *messages,
            ]
        )

    summary_msg = invoke_with_throttle_fallback(summarize)
    content = (
        summary_msg.content if isinstance(summary_msg.content, str) else str(summary_msg.content)
    )

    paths: list[dict] = []
    try:
        paths = _parse_paths_json(content)
    except (json.JSONDecodeError, TypeError):
        paths = _paths_from_tool_messages(messages)
        if paths:
            step_log.append("graph_walker: synthesized paths from tool results")
        else:
            paths = _heuristic_walk(query, chunks)
            step_log.append("graph_walker: fell back to heuristic walk")

    if not paths:
        paths = _heuristic_walk(query, chunks)
        step_log.append("graph_walker: empty LLM paths — heuristic walk")

    if not paths:
        paths = [{"nodes": [], "rels": [], "rationale": "no graph entities found"}]

    step_log.append(f"graph_walker: {len(paths)} paths")
    return {"graph_paths": paths, "step_log": step_log}
