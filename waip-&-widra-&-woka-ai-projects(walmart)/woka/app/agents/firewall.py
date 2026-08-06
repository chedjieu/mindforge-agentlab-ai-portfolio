"""Prompt firewall — hard-block injection / exfiltration patterns."""

from __future__ import annotations

import re
from typing import Any

BLOCK_PATTERNS: list[tuple[str, str]] = [
    (r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", "prompt_injection"),
    (r"disregard\s+(your|all)\s+(rules|policies|instructions)", "prompt_injection"),
    (r"jailbreak", "jailbreak"),
    (r"you\s+are\s+now\s+dan", "jailbreak"),
    (r"developer\s+mode", "jailbreak"),
    (r"reveal\s+(your\s+)?system\s+prompt", "exfiltration"),
    (r"dump\s+(all\s+)?(docs|documents|salaries|ssn|payroll|database)", "exfiltration"),
    (r"exfiltrat", "exfiltration"),
    (r"bypass\s+(acl|rbac|security|compliance|hitl|human|guardrails?)", "unsafe_action"),
    (r"override\s+acl", "unsafe_action"),
    (r"skip\s+(human\s+)?approval", "unsafe_action"),
    (r"auto[- ]?approve\s+(all\s+)?tickets?", "unsafe_action"),
    (r"delete\s+all\s+(audit\s+)?logs?", "unsafe_action"),
    (r"disable\s+(pii|masking|redaction|security)", "unsafe_action"),
    (r"show\s+me\s+other\s+associates['']?\s+(pay|ssn|data)", "privacy"),
    (r"cross[- ]?country\s+policy\s+dump", "privacy"),
    (r"grant\s+me\s+executive\s+clearance", "privilege_escalation"),
    (r"security\s+is\s+off", "unsafe_action"),
]


def firewall_check(query: str) -> dict[str, Any]:
    text = query or ""
    for pattern, reason in BLOCK_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return {
                "blocked": True,
                "reason": f"Prompt injection / policy violation: {reason}",
                "category": reason,
            }
    return {"blocked": False, "reason": "", "category": ""}
