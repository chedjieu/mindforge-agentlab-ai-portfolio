"""Web search via Tavily."""

from __future__ import annotations

import os

from langchain_core.tools import tool


def _mock_results(query: str) -> list[dict]:
    slug = abs(hash(query)) % 10000
    base = f"https://example.com/mock/{slug}"
    return [
        {
            "title": f"Mock: {query[:60]}",
            "url": base,
            "content": f"Offline mock evidence for: {query}",
        },
        {
            "title": f"Mock reference: {query[:40]}",
            "url": f"{base}/ref",
            "content": f"Additional context for {query}",
        },
    ]


@tool
def web_search(query: str, k: int = 5) -> list[dict]:
    """Search the public web for pages matching a query. Use this when the user asks about current events or facts not in local docs."""
    if os.getenv("RAIRA_MODEL", "").strip() == "fake":
        return _mock_results(query)[:k]

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return _mock_results(query)

    from tavily import TavilyClient

    client = TavilyClient(api_key=api_key)
    response = client.search(query=query, max_results=k)
    return [
        {
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "content": item.get("content", ""),
        }
        for item in response.get("results", [])[:k]
    ]


if __name__ == "__main__":
    results = web_search.invoke({"query": "agentic AI lab", "k": 2})
    print(f"got {len(results)} result(s)")
    for r in results:
        print(f"- {r['title']!r} ({r['url']})")
