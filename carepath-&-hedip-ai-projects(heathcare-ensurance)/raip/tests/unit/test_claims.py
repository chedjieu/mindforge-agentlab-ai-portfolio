from app.grounding.engine import extract_claims, verify_claims
from app.models.contracts import EvidencePassage, SupportStatus


def test_extract_and_support_metformin() -> None:
    draft = (
        "First-line pharmacologic therapy for adults with type 2 diabetes is metformin unless contraindicated."
    )
    ev = [
        EvidencePassage(
            chunk_id="c1",
            document_id="d1",
            version_id="v2",
            version_number="2.0",
            title="NEC GL",
            page_number=2,
            section="Recommendations",
            text=draft,
            authority_tier="2_guideline",
            score=1.0,
        )
    ]
    claims, _ = verify_claims(extract_claims(draft), ev, tenant_id="t")
    assert any(c.support_status == SupportStatus.SUPPORTED for c in claims)
    assert claims[0].evidence[0].page == 2


def test_evidence_gap_not_applicable() -> None:
    claims = extract_claims(
        "EVIDENCE GAP\nThe available approved sources do not provide sufficient evidence to support this statement."
    )
    assert any(c.support_status == SupportStatus.NOT_APPLICABLE for c in claims)
