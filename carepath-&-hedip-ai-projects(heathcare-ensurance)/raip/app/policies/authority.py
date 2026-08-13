"""Authority comparison helpers."""

from __future__ import annotations

from typing import Any

from app.models.contracts import TIER_RANK


def prefer_source(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    if a.get("superseded") and not b.get("superseded"):
        return b
    if b.get("superseded") and not a.get("superseded"):
        return a
    ra, rb = TIER_RANK.get(str(a.get("tier")), 9), TIER_RANK.get(str(b.get("tier")), 9)
    if ra != rb:
        return a if ra < rb else b
    return b if str(b.get("effective_date") or "") > str(a.get("effective_date") or "") else a
