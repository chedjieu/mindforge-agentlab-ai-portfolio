"""Semantic org memory."""

from __future__ import annotations

_ORG = {
    "client-retailco": {"industry": "retail", "cloud": "AWS", "voice": "outcome-first"},
    "client-eduboard": {"industry": "education", "cloud": "AWS", "voice": "academic clarity"},
    "client-carenet": {"industry": "healthcare", "cloud": "AWS", "voice": "clinical trust"},
}


def recall_org(client_id: str) -> dict:
    return dict(_ORG.get(client_id, {"notes": "no semantic facts yet", "cloud": "AWS"}))
