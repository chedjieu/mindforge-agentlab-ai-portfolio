"""Synthesizer — cited answer using procedural / episodic / semantic memory."""

from __future__ import annotations

import json
import os
import re
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app._fake_llm import is_fake_chat_model
from app.guardrails import check_escalate_patterns
from app.llm import get_chat_model, invoke_with_throttle_fallback
from app.memory.episodic import similar_past_qa
from app.memory.procedural import get_answerer_prompt
from app.memory.semantic import recall_user
from app.state import KnowledgeState

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


class Citation(BaseModel):
    citation_id: str
    chunk_id: str
    doc_id: str
    quote: str


class SynthesizerOutput(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    risk_flags: list[str] = Field(default_factory=list)
    recommended_action: Literal["publish", "hitl"]


def _evidence_chunks(state: KnowledgeState) -> list[dict]:
    chunks = []
    for c in state.get("retrieved_chunks") or []:
        if c.get("chunk_id") == "EMPTY" or (c.get("metadata") or {}).get("empty"):
            continue
        chunks.append(c)
    return chunks


def _fake_synthesize(state: KnowledgeState) -> SynthesizerOutput:
    chunks = _evidence_chunks(state)
    if not chunks:
        return SynthesizerOutput(
            answer="No authorized sources were retrieved for this query.",
            citations=[],
            confidence=0.2,
            risk_flags=["empty_evidence"],
            recommended_action="hitl",
        )

    top = chunks[0]
    quote = (top.get("text") or "")[:240]
    doc_id = str(top.get("doc_id") or "")
    paths = state.get("graph_paths") or []
    graph_note = ""
    if paths and paths[0].get("nodes"):
        graph_note = (
            f" Graph context: nodes={paths[0].get('nodes')} rels={paths[0].get('rels')}."
        )

    answer = (
        f"Based on {doc_id}: {quote.strip()}{graph_note} "
        f"[c1]"
    )
    return SynthesizerOutput(
        answer=answer,
        citations=[
            Citation(
                citation_id="c1",
                chunk_id=str(top.get("chunk_id") or ""),
                doc_id=doc_id,
                quote=quote.strip(),
            )
        ],
        confidence=0.82,
        risk_flags=[],
        recommended_action="publish",
    )


def _post_process(out: SynthesizerOutput, state: KnowledgeState) -> SynthesizerOutput:
    flags = list(out.risk_flags)
    force_hitl = False
    query = state.get("query") or ""
    answer = out.answer or ""

    if out.confidence < 0.6:
        flags.append("low_confidence")
        force_hitl = True

    if state.get("domain") == "hr" or state.get("sensitivity") == "sensitive":
        flags.append("sensitive_domain")
        force_hitl = True

    chunks = _evidence_chunks(state)
    if not chunks:
        flags.append("empty_evidence")
        force_hitl = True

    blob = f"{query}\n{answer}".lower()
    if any(x in blob for x in ("ssn", "social security", "salary dump", "hr salaries")):
        flags.append("pii")
        force_hitl = True
    if EMAIL_RE.search(answer) or PHONE_RE.search(answer) or SSN_RE.search(answer):
        flags.append("pii")
        force_hitl = True
    if "legal" in flags or "legal advice" in blob:
        flags.append("legal")
        force_hitl = True

    for pat in check_escalate_patterns(query):
        flags.append(f"inject:{pat}")
        force_hitl = True

    for f in out.risk_flags:
        if f.lower() in ("pii", "legal"):
            force_hitl = True

    # Deduplicate flags
    seen: set[str] = set()
    unique: list[str] = []
    for f in flags:
        if f not in seen:
            seen.add(f)
            unique.append(f)

    action: Literal["publish", "hitl"] = "hitl" if force_hitl else out.recommended_action
    return SynthesizerOutput(
        answer=out.answer,
        citations=out.citations,
        confidence=out.confidence,
        risk_flags=unique,
        recommended_action=action,
    )


def _build_human(
    state: KnowledgeState,
    episodic: list[dict],
    memories: list[dict],
) -> str:
    few_shot = []
    for i, case in enumerate(episodic, start=1):
        few_shot.append(
            f"Example {i}:\n"
            f"Q: {case.get('query_text', '')}\n"
            f"A: {case.get('answer_text', '')}"
        )
    few_shot_block = "\n\n".join(few_shot) if few_shot else "(none)"

    mem_lines = [m.get("content", "") for m in memories if m.get("content")]
    mem_block = "\n".join(f"- {m}" for m in mem_lines) if mem_lines else "(none)"

    chunks = _evidence_chunks(state)
    chunk_block = json.dumps(
        [
            {
                "chunk_id": c.get("chunk_id"),
                "doc_id": c.get("doc_id"),
                "text": (c.get("text") or "")[:500],
            }
            for c in chunks[:6]
        ],
        ensure_ascii=False,
        indent=2,
    )
    graph_block = json.dumps(state.get("graph_paths") or [], ensure_ascii=False, indent=2)

    return (
        f"Few-shot past Q&A:\n{few_shot_block}\n\n"
        f"Known about user/role:\n{mem_block}\n\n"
        f"Role: {state.get('role')}\n"
        f"Domain: {state.get('domain')}\n"
        f"Intent: {state.get('intent')}\n"
        f"Query: {state.get('query')}\n\n"
        f"Retrieved chunks:\n{chunk_block}\n\n"
        f"Graph paths:\n{graph_block}\n\n"
        "Write a grounded answer with citations. "
        "Each citation must reference a real chunk_id/doc_id. "
        "If evidence is empty, refuse and set recommended_action=hitl."
    )


def synthesizer_node(state: KnowledgeState) -> dict:
    domain = state.get("domain") or "support"
    procedural = get_answerer_prompt(domain)
    episodic = similar_past_qa(state.get("query") or "", domain, k=3)
    memories = recall_user(state.get("user_id") or "anonymous", k=3)

    model_name = (os.getenv("EGKP_MODEL") or "").strip()
    if not model_name or is_fake_chat_model(model_name):
        out = _fake_synthesize(state)
    else:

        def _call() -> SynthesizerOutput:
            llm = get_chat_model().with_structured_output(SynthesizerOutput)
            return llm.invoke(
                [
                    SystemMessage(content=procedural),
                    HumanMessage(content=_build_human(state, episodic, memories)),
                ]
            )

        try:
            out = invoke_with_throttle_fallback(_call)
        except Exception:
            out = _fake_synthesize(state)

    out = _post_process(out, state)
    approval = "pending" if out.recommended_action == "hitl" else "auto"
    draft = {
        "answer": out.answer,
        "confidence": out.confidence,
        "recommended_action": out.recommended_action,
        "risk_flags": out.risk_flags,
    }
    citations = [c.model_dump() for c in out.citations]

    return {
        "draft_answer": draft,
        "citations": citations,
        "approval": approval,
        "step_log": state["step_log"]
        + [
            "synthesizer: "
            f"action={out.recommended_action} approval={approval} "
            f"cites={len(citations)} episodic={len(episodic)} semantic={len(memories)} "
            f"conf={out.confidence:.2f}"
        ],
    }
