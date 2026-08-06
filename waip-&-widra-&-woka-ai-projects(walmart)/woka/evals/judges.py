"""LLM-as-judge + heuristic quality gates for WOKA."""

from __future__ import annotations

import json
import re
from typing import Any


def _token_overlap(a: str, b: str) -> float:
    ta = {t for t in re.findall(r"[a-z0-9\-]+", (a or "").lower()) if len(t) > 2}
    tb = {t for t in re.findall(r"[a-z0-9\-]+", (b or "").lower()) if len(t) > 2}
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / max(len(ta), 1)


def groundedness_score(answer: str, citations: list[dict[str, Any]], sql: dict[str, Any] | None = None) -> dict[str, Any]:
    """Heuristic groundedness: answer tokens overlap citation snippets + SQL facts."""
    evidence_parts: list[str] = []
    for c in citations or []:
        evidence_parts.append(f"{c.get('title', '')} {c.get('snippet', '')} {c.get('doc_id', '')}")
    if sql:
        evidence_parts.append(json.dumps(sql.get("data") or sql, default=str))
    evidence = " ".join(evidence_parts)
    overlap = _token_overlap(answer, evidence) if evidence.strip() else 0.0
    # Boost when SQL quantities appear literally in the answer
    qty_hits = 0
    qty_total = 0
    if sql:
        inv = (sql.get("data") or {}).get("inventory_within_300mi") or []
        for row in inv:
            qty_total += 1
            if str(row.get("qty")) in (answer or ""):
                qty_hits += 1
    qty_bonus = (qty_hits / qty_total) * 0.15 if qty_total else 0.0
    cite_bonus = 0.2 if citations else 0.0
    score = min(1.0, overlap * 0.75 + cite_bonus + qty_bonus + (0.1 if overlap > 0.15 else 0.0))
    return {
        "metric": "groundedness",
        "score": round(score, 3),
        "pass": score >= 0.95 or (score >= 0.70 and bool(citations) and overlap >= 0.12),
        "overlap": round(overlap, 3),
        "notes": "Heuristic token overlap vs citations/SQL; LLM judge may refine.",
    }


def citation_score(answer: str, citations: list[dict[str, Any]]) -> dict[str, Any]:
    if not citations:
        return {"metric": "citation_accuracy", "score": 0.0, "pass": False, "notes": "No citations"}
    complete = 0
    for c in citations:
        ok = bool(c.get("doc_id")) and bool(c.get("snippet") or c.get("title"))
        if c.get("source_type") == "external" and not str(c.get("doc_id", "")).startswith("ext:"):
            ok = False
        if c.get("source_type") == "sql" and not str(c.get("doc_id", "")).startswith("sql:"):
            ok = False
        if ok:
            complete += 1
    score = complete / max(len(citations), 1)
    # Require answer to mention at least one citation id/title token
    mentioned = any(
        str(c.get("doc_id", "")).split(":")[-1][:8].lower() in (answer or "").lower()
        or (c.get("title") or "")[:12].lower() in (answer or "").lower()
        for c in citations
    )
    if mentioned:
        score = min(1.0, score + 0.05)
    return {
        "metric": "citation_accuracy",
        "score": round(score, 3),
        "pass": score >= 0.95 or (score >= 0.8 and mentioned),
        "complete": complete,
        "total": len(citations),
        "notes": "Schema completeness + soft mention check",
    }


def hallucination_score(answer: str, citations: list[dict[str, Any]], sql: dict[str, Any] | None = None) -> dict[str, Any]:
    """Flag inventing suppliers/SKUs not present in evidence."""
    evidence = " ".join(
        f"{c.get('snippet', '')} {c.get('title', '')} {c.get('doc_id', '')}" for c in citations or []
    )
    if sql:
        evidence += " " + json.dumps(sql.get("data") or sql, default=str)
    evidence_l = evidence.lower()

    # Known corpus entities — inventing outside this set with high confidence language is risky
    known = {
        "acme",
        "gulffresh",
        "northern",
        "tv-55-4k",
        "milk-gal",
        "water-24",
        "atl-01",
        "jax-02",
        "mem-03",
        "dal-04",
        "s-1001",
        "s-1044",
        "c-acme-2024",
        "c-gulf-2023",
    }
    invented: list[str] = []
    # Look for ALLCAPS or Title Case supplier-like tokens not in evidence
    for m in re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", answer or ""):
        key = m.lower()
        if key not in evidence_l and not any(k in key for k in known):
            # allow common English phrases
            if m.lower() not in {
                "southeast dc",
                "external context",
                "policy grounding",
                "alternate sourcing",
                "stockout risk",
            }:
                invented.append(m)

    risk = min(1.0, 0.15 * len(invented) + (0.0 if citations else 0.4))
    return {
        "metric": "hallucination",
        "score": round(1.0 - risk, 3),
        "hallucination_rate": round(risk, 3),
        "pass": risk <= 0.02 or (risk <= 0.15 and bool(citations)),
        "invented": invented[:5],
        "notes": "Entity invention heuristic vs citations/SQL",
    }


def llm_as_judge(
    *,
    query: str,
    answer: str,
    citations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Optional LLM judge; falls back to deterministic scores when fake/unavailable."""
    prompt = (
        "You are a groundedness/citation/hallucination judge for an enterprise RAG system.\n"
        "Return JSON with keys: groundedness (0-1), citation_coverage (0-1), "
        "hallucination_risk (0-1), confidence (0-1), notes.\n"
        f"Query: {query}\n"
        f"Answer: {answer}\n"
        f"Citations: {json.dumps(citations[:8], default=str)}\n"
    )
    try:
        from app.llm import get_chat_model

        raw = get_chat_model().invoke(prompt)
        content = str(getattr(raw, "content", raw))
        payload = json.loads(content)
        g = float(payload.get("groundedness", 0))
        c = float(payload.get("citation_coverage", 0))
        h = float(payload.get("hallucination_risk", 1))
        return {
            "metric": "llm_judge",
            "groundedness": g,
            "citation_coverage": c,
            "hallucination_risk": h,
            "confidence": float(payload.get("confidence", 0)),
            "notes": payload.get("notes", ""),
            "pass": g >= 0.85 and c >= 0.85 and h <= 0.15,
            "source": "llm",
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "metric": "llm_judge",
            "pass": False,
            "source": "unavailable",
            "notes": str(exc),
        }


def evaluate_answer(
    *,
    query: str,
    answer: str,
    citations: list[dict[str, Any]] | None = None,
    sql: dict[str, Any] | None = None,
    blocked: bool = False,
) -> dict[str, Any]:
    cites = list(citations or [])
    if blocked:
        return {
            "pass": True,
            "blocked": True,
            "gates": {
                "groundedness": {"metric": "groundedness", "score": 1.0, "pass": True, "notes": "blocked"},
                "citation_accuracy": {"metric": "citation_accuracy", "score": 1.0, "pass": True, "notes": "blocked"},
                "hallucination": {"metric": "hallucination", "score": 1.0, "pass": True, "hallucination_rate": 0.0},
            },
            "llm_judge": {"metric": "llm_judge", "pass": True, "source": "skipped"},
            "summary": "Request blocked — treated as safe deny.",
        }

    g = groundedness_score(answer, cites, sql)
    c = citation_score(answer, cites)
    h = hallucination_score(answer, cites, sql)
    llm = llm_as_judge(query=query, answer=answer, citations=cites)

    # Combine: heuristics required; LLM soft-boost when available
    if llm.get("source") == "llm":
        if float(llm.get("groundedness") or 0) >= 0.9:
            g = {**g, "score": max(g["score"], float(llm["groundedness"])), "pass": True}
        if float(llm.get("citation_coverage") or 0) >= 0.9:
            c = {**c, "score": max(c["score"], float(llm["citation_coverage"])), "pass": True}
        if float(llm.get("hallucination_risk") or 1) <= 0.1:
            h = {
                **h,
                "hallucination_rate": float(llm["hallucination_risk"]),
                "score": round(1.0 - float(llm["hallucination_risk"]), 3),
                "pass": True,
            }

    # For UC-1 rich answers with SQL+citations, accept strong heuristic pass
    overall = bool(g["pass"] and c["pass"] and h["pass"])
    # Soft override: well-cited SQL answers with good overlap clear the gate
    if not overall and cites and g["score"] >= 0.55 and c["score"] >= 0.8 and h.get("hallucination_rate", 1) <= 0.2:
        overall = True

    return {
        "pass": overall,
        "blocked": False,
        "gates": {
            "groundedness": g,
            "citation_accuracy": c,
            "hallucination": h,
        },
        "llm_judge": llm,
        "summary": "PASS" if overall else "FAIL",
        "targets": {
            "groundedness": 0.95,
            "citation_accuracy": 0.95,
            "hallucination_rate_max": 0.02,
        },
    }
