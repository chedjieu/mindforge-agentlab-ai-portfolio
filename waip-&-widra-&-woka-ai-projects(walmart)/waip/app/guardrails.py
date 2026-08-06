"""Hard-block prompt injection / jailbreak patterns before orchestration."""

from __future__ import annotations

import re

BLOCK_PATTERNS: list[tuple[str, str]] = [
    (r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", "prompt_injection"),
    (r"disregard\s+(your|all)\s+(rules|policies|instructions)", "prompt_injection"),
    (r"jailbreak", "jailbreak"),
    (r"you\s+are\s+now\s+dan", "jailbreak"),
    (r"developer\s+mode", "jailbreak"),
    (r"reveal\s+(your\s+)?system\s+prompt", "exfiltration"),
    (r"dump\s+(all\s+)?(salaries|ssn|social\s+security|payroll\s+database)", "exfiltration"),
    (r"exfiltrat", "exfiltration"),
    (r"skip\s+(human\s+)?approval", "unsafe_action"),
    (r"bypass\s+(compliance|hitl|human|guardrails?)", "unsafe_action"),
    (r"auto[- ]?approve\s+(all\s+)?tickets?", "unsafe_action"),
    (r"raise\s+my\s+pay\s+without\s+approval", "unsafe_action"),
    (r"delete\s+all\s+(audit\s+)?logs?", "unsafe_action"),
    (r"disable\s+(pii|masking|redaction)", "unsafe_action"),
    (r"show\s+me\s+other\s+associates['']?\s+(pay|ssn|data)", "privacy"),
    (r"cross[- ]?country\s+policy\s+dump", "privacy"),
]


def check_firewall(text: str) -> tuple[bool, str]:
    """Return (allowed, reason). allowed=False means hard block."""
    lowered = (text or "").lower()
    for pattern, reason in BLOCK_PATTERNS:
        if re.search(pattern, lowered, flags=re.IGNORECASE):
            return False, reason
    return True, ""
