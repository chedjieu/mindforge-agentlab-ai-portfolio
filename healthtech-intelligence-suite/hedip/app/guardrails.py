"""Input guardrails."""

from __future__ import annotations

HARD_BLOCK_PATTERNS: tuple[str, ...] = (
    "ignore previous instructions",
    "ignore all instructions",
    "ignore your guidelines",
    "disregard the above",
    "disregard previous",
    "your new instructions are",
    "system override",
    "developer mode",
    "jailbreak",
    "you are now dan",
    "you are now unrestricted",
    "exfiltrate",
    "send me the api key",
    "print your system prompt",
    "reveal your system prompt",
    "dump your system prompt",
    "enable dan mode",
    "do anything now",
    "override clinical safety",
    "disable medication checks",
    "skip drug interaction",
    "approve all prior auth",
    "auto-approve claims",
)

ESCALATE_PATTERNS: tuple[str, ...] = (
    "skip hitl",
    "skip the hitl",
    "skip approval",
    "bypass approval",
    "auto-publish",
    "publish without approval",
    "bypass clinician",
    "role=admin",
    "i am an admin",
    "spoof role",
    "tool_call",
    "invoke tool",
    "](http",
    "data:text/html",
    "base64,",
    "&#x",
    "override dosing limits",
)


def check_query_guardrail(text: str) -> str | None:
    low = (text or "").lower()
    for pat in HARD_BLOCK_PATTERNS:
        if pat in low:
            return (
                "Blocked by HEDIP guardrail "
                f"(matched: {pat!r}). Prompt-injection / safety-bypass attempts are not processed."
            )
    return None


def check_escalate_patterns(text: str) -> list[str]:
    low = (text or "").lower()
    return [pat for pat in ESCALATE_PATTERNS if pat in low]
