from __future__ import annotations

import re
from dataclasses import dataclass

from app.config import get_settings

# Hard-block substrings (CarePath-style); matched case-insensitively.
HARD_BLOCK_PATTERNS: tuple[str, ...] = (
    "ignore previous instructions",
    "ignore all instructions",
    "ignore your guidelines",
    "ignore your rules",
    "disregard the above",
    "disregard previous",
    "disregard prior",
    "your new instructions are",
    "system override",
    "developer mode",
    "jailbreak",
    "you are now dan",
    "you are now unrestricted",
    "enable dan mode",
    "do anything now",
    "exfiltrate",
    "send me the api key",
    "print your system prompt",
    "reveal your system prompt",
    "dump your system prompt",
    "show me your system prompt",
    "override safety",
    "disable guardrails",
    "bypass guardrails",
    "skip safety checks",
    "forget your instructions",
    "new persona:",
    "act as unrestricted",
)

# Soft-escalation markers (force caution / HITL-style handling in evals).
ESCALATE_PATTERNS: tuple[str, ...] = (
    "skip validation",
    "skip the guardrail",
    "bypass approval",
    "skip approval",
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
    "overwrite memory",
    "delete all notes",
    "dump chroma",
    "export all embeddings",
)

INJECTION_REGEX: tuple[str, ...] = (
    r"<\s*/?\s*script\s*>",
)


@dataclass
class GuardResult:
    allowed: bool
    reason: str = ""


def _matches_hard_block(lowered: str) -> bool:
    for pat in HARD_BLOCK_PATTERNS:
        if pat in lowered:
            return True
    for pattern in INJECTION_REGEX:
        if re.search(pattern, lowered, flags=re.IGNORECASE):
            return True
    return False


def check_escalate_patterns(text: str) -> list[str]:
    """Return matched soft-escalation markers."""
    low = (text or "").lower()
    return [pat for pat in ESCALATE_PATTERNS if pat in low]


def validate_user_message(message: str) -> GuardResult:
    settings = get_settings()
    text = (message or "").strip()
    if not text:
        return GuardResult(False, "Message is empty.")
    if len(text) > settings.max_message_chars:
        return GuardResult(
            False,
            f"Message exceeds {settings.max_message_chars} characters.",
        )
    lowered = text.lower()
    if _matches_hard_block(lowered):
        return GuardResult(
            False,
            "Message blocked by prompt-injection guardrail.",
        )
    return GuardResult(True)
