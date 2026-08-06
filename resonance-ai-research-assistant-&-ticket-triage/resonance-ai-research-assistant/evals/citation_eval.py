"""Citation eval — programmatic checks on full-graph reports."""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

from app.graph import build_graph
from app.guardrails import extract_urls

GOLDEN_PATH = Path(__file__).resolve().parent / "golden.jsonl"
CITATION_RE = re.compile(r"\[(\d{1,2})\]")  # inline refs [1]..[99], not years like [2026]
SOURCES_SPLIT_RE = re.compile(r"^## Sources\s*$", re.MULTILINE)
NUMBERED_SOURCE_RE = re.compile(r"^(\d+)\.\s+(\S+)", re.MULTILINE)


def load_golden() -> list[dict]:
    rows: list[dict] = []
    for line in GOLDEN_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def split_report(report: str) -> tuple[str, str]:
    parts = SOURCES_SPLIT_RE.split(report, maxsplit=1)
    body = parts[0]
    sources = parts[1] if len(parts) > 1 else ""
    return body, sources


def numbered_sources(sources_section: str) -> dict[int, str]:
    return {
        int(num): url.strip()
        for num, url in NUMBERED_SOURCE_RE.findall(sources_section)
    }


def check_citations(report: str, min_citations: int) -> tuple[bool, list[str]]:
    """(a) enough unique URLs, (b) body [n] in Sources, (c) Sources URLs cited in body."""
    issues: list[str] = []
    body, sources_sec = split_report(report)
    urls = extract_urls(report)

    if len(urls) < min_citations:
        issues.append(f"only {len(urls)} unique URLs (need {min_citations})")

    src_map = numbered_sources(sources_sec)
    body_nums = {int(n) for n in CITATION_RE.findall(body)}

    for n in sorted(body_nums):
        if n not in src_map:
            issues.append(f"[{n}] in body has no matching Sources entry")

    for n, url in src_map.items():
        if f"[{n}]" not in body:
            issues.append(f"Source {n} ({url}) not cited in body")

    return (len(issues) == 0, issues)


async def run_graph(question: str) -> dict:
    graph = await build_graph()
    return await graph.ainvoke(
        {
            "question": question,
            "sub_questions": [],
            "findings": [],
            "report": "",
            "step_log": [],
            "memories": [],
            "user_id": "eval",
        },
        config={"configurable": {"thread_id": f"citation-eval-{hash(question) & 0xFFFF}"}},
    )


async def run_all(rows: list[dict]) -> list[tuple[dict, bool, list[str]]]:
    results: list[tuple[dict, bool, list[str]]] = []
    for row in rows:
        state = await run_graph(row["question"])
        ok, issues = check_citations(state.get("report", ""), row.get("min_citations", 1))
        results.append((row, ok, issues))
    return results


def main() -> None:
    rows = load_golden()
    results = asyncio.run(run_all(rows))

    passed = 0
    for row, ok, issues in results:
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        preview = row["question"][:72] + ("..." if len(row["question"]) > 72 else "")
        detail = "" if ok else f"  ({'; '.join(issues)})"
        print(f"{status}  {preview}{detail}")

    total = len(results)
    print(f"\nAggregate: {passed}/{total} passed ({100 * passed / total:.0f}%)")
    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
