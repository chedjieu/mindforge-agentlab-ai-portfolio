from app.ingestion.intelligence import authority_score
from app.models.contracts import TIER_RANK, AuthorityTier
from app.policies.authority import prefer_source


def test_tier_order() -> None:
    assert TIER_RANK[str(AuthorityTier.REGULATORY)] < TIER_RANK[str(AuthorityTier.GUIDELINE)]
    assert authority_score(str(AuthorityTier.REGULATORY)) > authority_score(str(AuthorityTier.UNVERIFIED))


def test_prefer_higher_authority_and_newer() -> None:
    a = {"tier": str(AuthorityTier.GUIDELINE), "effective_date": "2022-01-01", "superseded": True}
    b = {"tier": str(AuthorityTier.GUIDELINE), "effective_date": "2024-03-01", "superseded": False}
    assert prefer_source(a, b) == b
