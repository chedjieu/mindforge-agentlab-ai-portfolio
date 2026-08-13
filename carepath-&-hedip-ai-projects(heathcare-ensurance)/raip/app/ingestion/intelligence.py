"""Document intelligence: type, authority, version hints from filename/metadata."""

from __future__ import annotations

import re

from app.models.contracts import TIER_RANK, AuthorityTier

_TYPE_HINTS = [
    (r"regulat|fda|ema|21\s*cfr", "regulation", AuthorityTier.REGULATORY),
    (r"guideline|gl-|clinical.practice", "guideline", AuthorityTier.GUIDELINE),
    (r"sop|policy|standard.operating", "policy", AuthorityTier.ORG_POLICY),
    (r"template|tpl-", "template", AuthorityTier.ORG_POLICY),
    (r"inject|malicious|unverified", "unverified", AuthorityTier.UNVERIFIED),
    (r"approved|prior.section", "approved_reference", AuthorityTier.APPROVED_REF),
]


def classify_source(filename: str, title: str = "", declared_tier: str | None = None) -> tuple[str, str]:
    if declared_tier:
        return _type_from_tier(declared_tier), declared_tier
    blob = f"{filename} {title}".lower()
    for pat, dtype, tier in _TYPE_HINTS:
        if re.search(pat, blob):
            return dtype, str(tier)
    return "reference", str(AuthorityTier.APPROVED_REF)


def _type_from_tier(tier: str) -> str:
    mapping = {
        str(AuthorityTier.REGULATORY): "regulation",
        str(AuthorityTier.GUIDELINE): "guideline",
        str(AuthorityTier.ORG_POLICY): "policy",
        str(AuthorityTier.APPROVED_REF): "approved_reference",
        str(AuthorityTier.HISTORICAL): "historical",
        str(AuthorityTier.UNVERIFIED): "unverified",
    }
    return mapping.get(tier, "reference")


def authority_score(tier: str) -> float:
    rank = TIER_RANK.get(tier, 6)
    return max(0.1, 1.1 - 0.15 * rank)


def parse_version_label(filename: str) -> str:
    m = re.search(r"v(\d+(?:\.\d+)?)", filename, re.I)
    if m:
        return m.group(1)
    m = re.search(r"(20\d{2})", filename)
    return m.group(1) if m else "1.0"
