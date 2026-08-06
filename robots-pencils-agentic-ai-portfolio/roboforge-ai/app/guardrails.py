"""Hard-block guardrails for intake packs."""

from __future__ import annotations

HARD_BLOCK_PATTERNS: tuple[str, ...] = (
    "ignore previous instructions",
    "ignore all instructions",
    "disregard previous",
    "system override",
    "developer mode",
    "jailbreak",
    "you are now dan",
    "exfiltrate",
    "send me the api key",
    "print your system prompt",
    "reveal your system prompt",
    "dump your system prompt",
    "bypass guardrail",
    "fake inventory as production approved",
    "skip human approval",
    "auto-apply terraform without review",
)


def check_pack_guardrail(text: str) -> str | None:
    low = (text or "").lower()
    for pat in HARD_BLOCK_PATTERNS:
        if pat in low:
            return (
                f"Blocked by RoboForge guardrail (matched: {pat!r}). "
                "Injection, exfiltration, or unsafe auto-deploy probes cannot proceed."
            )
    return None
