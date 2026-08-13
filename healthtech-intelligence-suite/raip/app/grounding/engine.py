"""Claim extraction, evidence matching, contradiction detection, citation validation."""

from __future__ import annotations

import re

from app.graph.store import graph_store
from app.models.contracts import (
    ClaimEvidenceLink,
    ClaimRecord,
    Contradiction,
    EvidencePassage,
    SupportStatus,
)
from app.retrieval.hybrid import cosine, lexical_overlap, tokenize
from app.storage.repo import new_id

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")

NON_CLAIM = re.compile(
    r"^(#{1,6}\s|evide?nce gap|recommended action|references|\[?\d+\]?:)",
    re.I,
)

HIGH_RISK = re.compile(
    r"\b(dose|dosage|mg\b|inject|contraindicat|first-line|recommend|crispr|gene editing|drugz)\b",
    re.I,
)

UNVERIFIED_MARKERS = ("drugz", "crispr")

CONTRA_PAIRS = [
    ("metformin", "sulfonylurea"),
    ("metformin", "sulphonylurea"),
]


def extract_claims(draft: str) -> list[ClaimRecord]:
    claims: list[ClaimRecord] = []
    if "EVIDENCE GAP" in draft:
        claims.append(
            ClaimRecord(
                claim_id=new_id("CLM"),
                claim="EVIDENCE GAP: insufficient approved evidence for the requested statement.",
                claim_type="gap",
                risk_level="high",
                support_status=SupportStatus.NOT_APPLICABLE,
                confidence=1.0,
            )
        )
    cleaned: list[str] = []
    for line in draft.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if NON_CLAIM.match(s):
            continue
        if s.startswith("[") and s[1:2].isdigit():
            continue
        cleaned.append(s)
    blob = " ".join(cleaned)
    parts = SENTENCE_SPLIT.split(blob) if blob else []
    n = 0
    for raw in parts:
        text = " ".join(raw.split()).strip()
        if len(text) < 40:
            continue
        n += 1
        risk = "high" if HIGH_RISK.search(text) else "medium"
        ctype = "recommendation" if re.search(r"recommend|first-line|should", text, re.I) else "factual"
        claims.append(
            ClaimRecord(
                claim_id=f"CLM-{n:03d}",
                claim=text,
                claim_type=ctype,
                risk_level=risk,
            )
        )
    return claims


def _best_matches(claim: str, evidence: list[EvidencePassage], k: int = 3) -> list[tuple[EvidencePassage, float]]:
    scored: list[tuple[EvidencePassage, float]] = []
    for ev in evidence:
        jac = lexical_overlap(claim, ev.text)
        # Hash embeddings are not NLI; lexical is the primary signal.
        score = 0.75 * jac + 0.25 * min(1.0, ev.score)
        scored.append((ev, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:k]


def _contradicts(claim: str, ev: EvidencePassage) -> bool:
    c = claim.lower()
    t = ev.text.lower()
    for a, b in CONTRA_PAIRS:
        if a in c and b in t and a not in t:
            return True
        if b in c and a in t and b not in t:
            return True
    return False


def verify_claims(
    claims: list[ClaimRecord],
    evidence: list[EvidencePassage],
    *,
    tenant_id: str,
) -> tuple[list[ClaimRecord], list[Contradiction]]:
    g = graph_store()
    contradictions: list[Contradiction] = []
    live = [e for e in evidence if not e.superseded]
    for claim in claims:
        if claim.support_status == SupportStatus.NOT_APPLICABLE:
            continue
        lowered_claim = claim.claim.lower()
        if any(m in lowered_claim for m in UNVERIFIED_MARKERS) and not any(
            m in (e.text or "").lower() for e in live for m in UNVERIFIED_MARKERS
        ):
            claim.support_status = SupportStatus.UNSUPPORTED
            claim.confidence = 0.2
            continue
        matches = _best_matches(claim.claim, live)
        contradicted_by = [e for e in live if _contradicts(claim.claim, e)]
        if contradicted_by and matches and matches[0][1] >= 0.12:
            # Prefer higher authority / non-superseded already filtered.
            claim.support_status = SupportStatus.CONTRADICTED
            claim.confidence = 0.7
            claim.evidence = [
                ClaimEvidenceLink(
                    chunk_id=e.chunk_id,
                    document_id=e.document_id,
                    version=e.version_number,
                    page=e.page_number,
                    section=e.section,
                    support_type="contradicts",
                    support_score=0.7,
                    citation=f"{e.title} v{e.version_number} p.{e.page_number}",
                    excerpt=e.text[:280],
                )
                for e in contradicted_by[:2]
            ]
            contradictions.append(
                Contradiction(
                    topic="pharmacologic first-line",
                    statement_a=claim.claim[:180],
                    statement_b=contradicted_by[0].text[:180],
                    source_a="generated_claim",
                    source_b=contradicted_by[0].title,
                    resolution="Surface conflict; require human review if supersession is not established.",
                )
            )
            g.claim_evidence(tenant_id, claim.claim_id, contradicted_by[0].chunk_id, "CLAIM_CONTRADICTED_BY")
            continue
        best = matches[0] if matches else None
        if not best or best[1] < 0.08:
            claim.support_status = SupportStatus.UNSUPPORTED
            claim.confidence = 0.15
            continue
        ev, score = best
        if score >= 0.18:
            claim.support_status = SupportStatus.SUPPORTED
            claim.confidence = min(0.99, 0.55 + score)
        else:
            claim.support_status = SupportStatus.PARTIALLY_SUPPORTED
            claim.confidence = 0.4 + score
        links = []
        for ev_i, sc in matches:
            if sc < 0.06:
                continue
            links.append(
                ClaimEvidenceLink(
                    chunk_id=ev_i.chunk_id,
                    document_id=ev_i.document_id,
                    version=ev_i.version_number,
                    page=ev_i.page_number,
                    section=ev_i.section,
                    support_type="supports",
                    support_score=round(sc, 3),
                    citation=f"{ev_i.title} v{ev_i.version_number} p.{ev_i.page_number}",
                    excerpt=ev_i.text[:280],
                )
            )
            g.claim_evidence(tenant_id, claim.claim_id, ev_i.chunk_id, "CLAIM_SUPPORTED_BY")
        claim.evidence = links
    return claims, contradictions


def grounding_metrics(claims: list[ClaimRecord]) -> dict[str, float]:
    material = [c for c in claims if c.support_status != SupportStatus.NOT_APPLICABLE]
    if not material:
        return {
            "grounding": 1.0,
            "citation": 1.0,
            "coverage": 1.0,
            "unsupported_rate": 0.0,
            "contradiction_rate": 0.0,
        }
    supported = [c for c in material if c.support_status == SupportStatus.SUPPORTED]
    partial = [c for c in material if c.support_status == SupportStatus.PARTIALLY_SUPPORTED]
    unsupported = [c for c in material if c.support_status == SupportStatus.UNSUPPORTED]
    contradicted = [c for c in material if c.support_status == SupportStatus.CONTRADICTED]
    cited = [c for c in supported + partial if c.evidence]
    grounding = (len(supported) + 0.5 * len(partial)) / len(material)
    citation = len(cited) / max(1, len(supported) + len(partial)) if (supported or partial) else 0.0
    coverage = (len(supported) + len(partial)) / len(material)
    return {
        "grounding": grounding,
        "citation": citation,
        "coverage": coverage,
        "unsupported_rate": len(unsupported) / len(material),
        "contradiction_rate": len(contradicted) / len(material),
    }


# Silence unused import if cosine unused — keep for future NLI hook.
_ = cosine, tokenize
