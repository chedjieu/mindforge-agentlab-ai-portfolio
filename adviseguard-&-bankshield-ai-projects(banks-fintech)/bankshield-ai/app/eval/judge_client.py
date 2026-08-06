"""Cross-provider LLM-as-judge client."""

from __future__ import annotations

import os
from typing import Any

from app._fake_llm import is_fake_chat_model
from app.llm import get_chat_model


def _provider(name: str) -> str:
    n = (name or "").lower()
    if "fake" in n:
        return "fake"
    if "bedrock" in n:
        return "bedrock"
    if "vertex" in n or "google" in n:
        return "vertex"
    return "other"


def assert_cross_provider() -> None:
    answerer = os.getenv("BANKSHIELD_MODEL", "fake")
    judge = os.getenv("BANKSHIELD_JUDGE_MODEL", "fake")
    if is_fake_chat_model(answerer) or is_fake_chat_model(judge):
        return
    if _provider(answerer) == _provider(judge):
        raise RuntimeError(
            "Judge model must be cross-provider vs answerer "
            f"(answerer={answerer}, judge={judge})"
        )


def judge_recommendation(state: dict[str, Any]) -> float | None:
    """Return 0–1 quality score; fake path returns heuristic None (caller uses local score)."""
    judge_name = os.getenv("BANKSHIELD_JUDGE_MODEL", "fake")
    if is_fake_chat_model(judge_name):
        return None
    assert_cross_provider()
    rec = state.get("recommendation") or {}
    prompt = (
        "Score the fraud recommendation groundedness from 0 to 1. "
        "Reply with only a float.\n"
        f"Summary: {rec.get('summary')}\nEvidence: {rec.get('evidence_ids')}\n"
        f"Citations: {rec.get('regulatory_refs')}"
    )
    msg = get_chat_model(judge_name).invoke([{"role": "user", "content": prompt}])
    try:
        return float(str(msg.content).strip().split()[0])
    except Exception:
        return None
