"""PII-ish detection on synthetic data only. Production would use a dedicated DLP service."""

from __future__ import annotations

import re

_PATTERNS = [
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\bMRN\s*[:=]\s*\w+", re.I),
]


def find_pii(text: str) -> list[str]:
    hits: list[str] = []
    for pat in _PATTERNS:
        hits.extend(m.group(0) for m in pat.finditer(text or ""))
    return hits
