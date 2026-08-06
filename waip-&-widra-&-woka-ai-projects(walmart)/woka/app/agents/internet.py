"""Internet Agent — curated external mocks (+ optional Tavily)."""

from __future__ import annotations

import os
from typing import Any

_WEATHER_MOCK = {
    "source": "NOAA Hurricane Advisory (mock)",
    "summary": (
        "Hurricane impacts Southeast coastal logistics corridors. "
        "Evacuation and closure orders affect ATL-01 and JAX-02 service areas."
    ),
    "impact_zone": "SE",
    "severity_level": "high",
}

_FDA_MOCK = {
    "source": "FDA advisory feed (mock)",
    "summary": "No active contamination recall tied to TV-55-4K or MILK-GAL in this scenario.",
    "relevance": "baseline",
}


def _tavily_search(query: str) -> list[dict[str, Any]]:
    key = os.getenv("TAVILY_API_KEY", "").strip()
    if not key:
        return []
    try:
        import httpx

        resp = httpx.post(
            "https://api.tavily.com/search",
            json={"api_key": key, "query": query, "max_results": 3},
            timeout=8.0,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        return [
            {
                "title": r.get("title"),
                "url": r.get("url"),
                "snippet": (r.get("content") or "")[:240],
                "source_type": "external",
            }
            for r in data.get("results", [])[:3]
        ]
    except Exception:  # noqa: BLE001
        return []


def run_internet_agent(query: str) -> dict[str, Any]:
    q = query.lower()
    items: list[dict[str, Any]] = []
    citations: list[dict[str, Any]] = []

    if any(k in q for k in ("hurricane", "weather", "storm", "southeast", "dc", "disruption")):
        items.append({"type": "weather", **_WEATHER_MOCK})
        citations.append(
            {
                "doc_id": "ext:weather",
                "title": _WEATHER_MOCK["source"],
                "page": 1,
                "section": "Impact zone",
                "snippet": _WEATHER_MOCK["summary"],
                "confidence": 0.9,
                "source_type": "external",
            }
        )

    if any(k in q for k in ("fda", "recall", "contamination")):
        items.append({"type": "fda", **_FDA_MOCK})
        citations.append(
            {
                "doc_id": "ext:fda",
                "title": _FDA_MOCK["source"],
                "page": 1,
                "section": "Advisory",
                "snippet": _FDA_MOCK["summary"],
                "confidence": 0.88,
                "source_type": "external",
            }
        )

    live = _tavily_search(query) if os.getenv("WOKA_ENABLE_TAVILY", "").lower() in {"1", "true", "yes"} else []
    for i, hit in enumerate(live):
        citations.append(
            {
                "doc_id": f"ext:tavily:{i}",
                "title": hit.get("title") or "Web result",
                "page": 0,
                "section": hit.get("url") or "",
                "snippet": hit.get("snippet") or "",
                "confidence": 0.7,
                "source_type": "external",
            }
        )

    if not items and not live:
        items.append(
            {
                "type": "note",
                "summary": "No external advisories matched; relying on internal sources.",
            }
        )

    return {
        "agent": "internet",
        "items": items,
        "live_results": live,
        "summary": "; ".join(i.get("summary", "") for i in items if i.get("summary")),
        "citations": citations,
    }
