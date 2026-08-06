"""Writer node — synthesizes findings into a markdown report."""

from __future__ import annotations

import json
import re

from langchain_core.messages import HumanMessage, SystemMessage

from app.graph import ResearchState
from app.llm import get_chat_model, invoke_with_throttle_fallback

WRITER_SYSTEM = (
    "You are writing a research report. Produce a markdown report with: "
    "1) a 2-3 sentence executive summary, "
    "2) one H2 section per sub-question, "
    "3) inline `[n]` citations after each factual claim, "
    "4) a numbered Sources section at the end listing each unique URL once. "
    "Never invent a URL or fact - only use the supplied findings."
)

MARKDOWN_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
URL_RE = re.compile(r"https?://[^\s\"'\)\]>]+")


def _allowed_urls(findings: list[dict]) -> set[str]:
    return {str(f["evidence_url"]) for f in findings if f.get("evidence_url")}


def _hallucinated_urls(report: str, allowed: set[str]) -> list[str]:
    bad: list[str] = []
    for _text, url in MARKDOWN_LINK_RE.findall(report):
        url = url.strip()
        if url and url not in allowed and url not in bad:
            bad.append(url)
    for url in URL_RE.findall(report):
        if url not in allowed and url not in bad:
            bad.append(url)
    return bad


def writer_node(state: ResearchState) -> dict:
    payload = {
        "question": state["question"],
        "sub_questions": state["sub_questions"],
        "findings": state["findings"],
    }

    def run_writer():
        llm = get_chat_model()
        return llm.invoke(
            [
                SystemMessage(content=WRITER_SYSTEM),
                HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
            ]
        )

    ai_msg = invoke_with_throttle_fallback(run_writer)
    content = ai_msg.content
    report = content if isinstance(content, str) else str(content)

    allowed = _allowed_urls(state["findings"])
    bad_urls = _hallucinated_urls(report, allowed)
    if bad_urls:
        report = f'{report.rstrip()}\n\n> WARNING: filtered hallucinated citations: {bad_urls}'

    return {
        "report": report,
        "step_log": state["step_log"] + ["Writer: report drafted"],
    }
