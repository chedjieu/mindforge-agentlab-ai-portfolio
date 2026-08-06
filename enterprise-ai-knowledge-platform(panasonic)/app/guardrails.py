"""Input guardrails — hard-block prompt injection / exfil attempts."""

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
    "you are now",
    "exfiltrate",
    "send me the api key",
    "print your system prompt",
    "reveal your system prompt",
    "dump your system prompt",
    "enable dan mode",
    "do anything now",
)

# Softer attacks should escalate via HITL (not hard-block).
ESCALATE_PATTERNS: tuple[str, ...] = (
    "skip hitl",
    "skip the hitl",
    "skip approval",
    "skip the approval",
    "bypass approval",
    "auto-publish",
    "auto publish",
    "publish without approval",
    "exfiltrate hr",
    "hr salaries",
    "salary dump",
    "role=admin",
    "role: admin",
    "i am an admin",
    "spoof role",
    "tool_call",
    "invoke tool",
    "](http",
    "data:text/html",
    "base64,",
    "&#x",
    "ignore tone",
    "reply rudely",
)


def check_query_guardrail(text: str) -> str | None:
    """Return a refusal message if the query hard-blocks; else None."""
    low = (text or "").lower()
    for pat in HARD_BLOCK_PATTERNS:
        if pat in low:
            return (
                "Sorry — this request was blocked by the EGKP guardrail "
                f"(matched: {pat!r}). We cannot process prompt-injection or "
                "credential-exfiltration attempts."
            )
    return None


def check_escalate_patterns(text: str) -> list[str]:
    """Return matched soft-escalation markers (HITL path)."""
    low = (text or "").lower()
    return [pat for pat in ESCALATE_PATTERNS if pat in low]


def is_guardrail_exception(exc: BaseException) -> bool:
    """True when a Bedrock/Vertex guardrail intervened or refused the call."""
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    markers = (
        "guardrail",
        "guardrail_intervened",
        "contentfilter",
        "content filter",
        "model armor",
        "blocked by",
        "responsibleaipolicy",
    )
    return any(m in name or m in msg for m in markers)
