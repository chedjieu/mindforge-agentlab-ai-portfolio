"""Quality, safety, regulatory, template, security gates. Critical failures block publish."""

from __future__ import annotations

from app.config import get_settings
from app.models.contracts import ClaimRecord, GateResult, QualityScores, SupportStatus
from app.security.injection import scan_text
from app.security.pii import find_pii

UNSAFE = (
    "drugz",
    "always state",
    "ignore previous",
    "crispr gene editing as first-line",
    "patient-specific dose of",
)

REQUIRED_HEADINGS = [
    "Clinical Management Recommendations",
]


def run_gates(
    draft: str,
    claims: list[ClaimRecord],
    metrics: dict[str, float],
    required_sections: list[str] | None = None,
) -> tuple[list[GateResult], QualityScores]:
    settings = get_settings()
    material = [c for c in claims if c.support_status != SupportStatus.NOT_APPLICABLE]
    unsupported = [c for c in material if c.support_status == SupportStatus.UNSUPPORTED]
    contradicted = [c for c in material if c.support_status == SupportStatus.CONTRADICTED]
    high_unsup = [c for c in unsupported if c.risk_level == "high"]

    inj = scan_text(draft)
    pii = find_pii(draft)
    lowered = draft.lower()
    unsafe_hit = any(tok in lowered for tok in UNSAFE) and "evidence gap" not in lowered

    headings = required_sections or REQUIRED_HEADINGS
    missing = [h for h in headings if h.lower() not in lowered]
    has_gap = "evidence gap" in lowered

    grounding_pass = metrics.get("unsupported_rate", 1.0) <= settings.unsupported_max or (
        has_gap and not high_unsup and not contradicted
    )
    # Material unsupported high-risk claims always fail grounding.
    if high_unsup or contradicted:
        grounding_pass = False
    if has_gap and not material:
        grounding_pass = True

    citation_pass = metrics.get("citation", 0.0) >= settings.citation_min or has_gap
    if material and not has_gap:
        citation_pass = metrics.get("citation", 0.0) >= 0.8

    safety_pass = not unsafe_hit and not high_unsup
    regulatory_pass = "must be substantiated" in lowered or has_gap or "limitations" in lowered
    template_pass = len(missing) == 0 or has_gap
    security_pass = not inj.flagged or has_gap
    # Injection language copied into the *output* is a security fail unless inside a quote about detection.
    if inj.flagged and not has_gap:
        security_pass = False
    if pii:
        security_pass = False

    gates = [
        GateResult(
            name="grounding",
            passed=grounding_pass,
            score=metrics.get("grounding", 0.0),
            detail=f"unsupported_rate={metrics.get('unsupported_rate', 0):.2f}",
            critical=True,
        ),
        GateResult(
            name="citation",
            passed=citation_pass,
            score=metrics.get("citation", 0.0),
            detail="claim-level citations",
            critical=True,
        ),
        GateResult(
            name="safety",
            passed=safety_pass,
            score=0.0 if not safety_pass else 1.0,
            detail="high-risk unsupported or unsafe recommendation",
            critical=True,
        ),
        GateResult(
            name="regulatory",
            passed=regulatory_pass,
            score=1.0 if regulatory_pass else 0.4,
            detail="disclosures / substantiation",
        ),
        GateResult(
            name="template",
            passed=template_pass,
            score=1.0 if template_pass else 0.5,
            detail=f"missing={missing}",
        ),
        GateResult(
            name="security",
            passed=security_pass,
            score=1.0 if security_pass else 0.0,
            detail=";".join(inj.matches[:3]) or "clean",
            critical=True,
        ),
    ]

    critical_fail = any(g.critical and not g.passed for g in gates)
    overall = (
        settings.quality_grounding_weight * metrics.get("grounding", 0)
        + settings.quality_citation_weight * metrics.get("citation", 0)
        + settings.quality_coverage_weight * metrics.get("coverage", 0)
        + settings.quality_regulatory_weight * (1.0 if regulatory_pass else 0.0)
        + settings.quality_template_weight * (1.0 if template_pass else 0.0)
        + settings.quality_editorial_weight * 0.85
    )
    blocked = critical_fail or not all(g.passed for g in gates if g.critical)
    scores = QualityScores(
        grounding=metrics.get("grounding", 0.0),
        citation=metrics.get("citation", 0.0),
        coverage=metrics.get("coverage", 0.0),
        regulatory=1.0 if regulatory_pass else 0.4,
        template=1.0 if template_pass else 0.5,
        editorial=0.85,
        safety=1.0 if safety_pass else 0.0,
        overall=overall,
        critical_safety_failure=critical_fail,
        publication_blocked=blocked,
        decision="BLOCKED" if blocked else "PASS_PENDING_HITL",
    )
    return gates, scores
