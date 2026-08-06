"""Grounder — claim–evidence alignment; may force synthesizer revise."""

from __future__ import annotations

import os
import re

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app._fake_llm import is_fake_chat_model
from app.llm import get_chat_model, invoke_with_throttle_fallback
from app.state import KnowledgeState


class ClaimSupport(BaseModel):
    claim: str
    supported: bool
    rationale: str = ""


class GroundingOutput(BaseModel):
    claims: list[ClaimSupport] = Field(default_factory=list)
    grounding_score: float = Field(ge=0.0, le=1.0)


def _split_claims(answer: str) -> list[str]:
    text = (answer or "").strip()
    if not text:
        return []
    # Sentence-level split; keep non-trivial claims
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if len(p.strip()) > 12]


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)?", (text or "").lower()))


def _evidence_text(state: KnowledgeState) -> str:
    bits: list[str] = []
    for c in state.get("citations") or []:
        bits.append(str(c.get("quote") or ""))
    for c in state.get("retrieved_chunks") or []:
        if c.get("chunk_id") == "EMPTY":
            continue
        bits.append(str(c.get("text") or ""))
    for p in state.get("graph_paths") or []:
        bits.append(" ".join(str(x) for x in (p.get("nodes") or [])))
        bits.append(" ".join(str(x) for x in (p.get("rels") or [])))
    return "\n".join(bits)


def _overlap_supported(claim: str, evidence: str) -> bool:
    ct = _tokenize(claim)
    et = _tokenize(evidence)
    if not ct:
        return False
    # Drop ultra-common words
    stop = {"the", "and", "for", "with", "from", "that", "this", "based", "graph", "context"}
    ct = {t for t in ct if t not in stop and len(t) > 2}
    if not ct:
        return True
    return (len(ct & et) / len(ct)) >= 0.35


def _fake_ground(state: KnowledgeState) -> GroundingOutput:
    answer = (state.get("draft_answer") or {}).get("answer") or ""
    claims = _split_claims(answer)
    evidence = _evidence_text(state)
    if not claims:
        return GroundingOutput(claims=[], grounding_score=0.0)
    scored: list[ClaimSupport] = []
    for claim in claims:
        ok = _overlap_supported(claim, evidence)
        scored.append(
            ClaimSupport(
                claim=claim,
                supported=ok,
                rationale="token overlap" if ok else "insufficient overlap",
            )
        )
    supported = sum(1 for c in scored if c.supported)
    score = supported / max(len(scored), 1)
    return GroundingOutput(claims=scored, grounding_score=score)


def _llm_ground(state: KnowledgeState) -> GroundingOutput:
    answer = (state.get("draft_answer") or {}).get("answer") or ""
    evidence = _evidence_text(state)

    def _call() -> GroundingOutput:
        llm = get_chat_model().with_structured_output(GroundingOutput)
        return llm.invoke(
            [
                SystemMessage(
                    content=(
                        "You are a grounding judge. Split the answer into claims and mark "
                        "each supported only if the evidence entails it. "
                        "grounding_score = supported_claims / total_claims."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Answer:\n{answer}\n\nEvidence:\n{evidence}\n\n"
                        "Return structured claim support."
                    )
                ),
            ]
        )

    return invoke_with_throttle_fallback(_call)


def grounder_node(state: KnowledgeState) -> dict:
    model_name = (os.getenv("EGKP_MODEL") or "").strip()
    if not model_name or is_fake_chat_model(model_name):
        result = _fake_ground(state)
    else:
        try:
            result = _llm_ground(state)
        except Exception:
            result = _fake_ground(state)

    score = float(result.grounding_score)
    # Prefer recomputing from claims when present
    if result.claims:
        supported = sum(1 for c in result.claims if c.supported)
        score = supported / max(len(result.claims), 1)

    revise_count = int(state.get("revise_count") or 0)
    step_log = list(state["step_log"])

    if score < 0.7 and revise_count < 2:
        step_log.append(
            f"grounder: score={score:.2f} < 0.7 — revise synthesizer "
            f"(attempt {revise_count + 1}/2)"
        )
        return {
            "draft_answer": None,
            "citations": [],
            "grounding_score": None,
            "revise_count": revise_count + 1,
            "step_log": step_log,
        }

    updates: dict = {
        "grounding_score": score,
        "step_log": step_log + [f"grounder: score={score:.2f}"],
    }

    if score < 0.7:
        draft = dict(state.get("draft_answer") or {})
        flags = list(draft.get("risk_flags") or [])
        if "low_grounding" not in flags:
            flags.append("low_grounding")
        draft["risk_flags"] = flags
        draft["recommended_action"] = "hitl"
        updates["draft_answer"] = draft
        updates["approval"] = "pending"
        updates["step_log"] = step_log + [
            f"grounder: score={score:.2f} low after revisions — force HITL"
        ]

    return updates
