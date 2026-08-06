"""Auto-prompt-tuning — propose v+1 answerer procedural prompt from HITL edits.

Prints to stdout only; does NOT write data/prompts/ automatically.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from langchain_core.messages import HumanMessage, SystemMessage

from app._fake_llm import is_fake_chat_model
from app.hitl_log import DEFAULT_LOG, load_hitl_outcomes
from app.llm import get_chat_model
from app.memory.procedural import get_answerer_prompt

REFINE_SYSTEM = (
    "You improve an enterprise knowledge answerer system prompt using HITL edits. "
    "Be concrete and conservative. Require citations. Never invent policy numbers, "
    "SLAs, or torque values. Prefer grounded, concise answers."
)

REFINE_HUMAN = """Domain: {domain}
Current procedural prompt:
---
{current_prompt}
---

HITL outcomes (last {n}, JSON). Focus on edit/reject and draft_before vs draft_after:
---
{outcomes_json}
---

Return JSON only:
{{
  "summary": ["...", "..."],
  "proposed_prompt": "...",
  "rationale": "one short paragraph"
}}
"""


def _parse_proposal(text: str) -> dict:
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    blob = fence.group(1).strip() if fence else text.strip()
    try:
        data = json.loads(blob)
        if isinstance(data, dict) and data.get("proposed_prompt"):
            return data
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return {
        "summary": ["(could not parse structured LLM reply)"],
        "proposed_prompt": text.strip(),
        "rationale": "fallback: used raw model output as proposed_prompt",
    }


def _heuristic_proposal(current: str, outcomes: list[dict]) -> dict:
    edits = [o for o in outcomes if o.get("action") == "edit"]
    rejects = [o for o in outcomes if o.get("action") == "reject"]
    summary = [
        f"{len(edits)} edits and {len(rejects)} rejects in the last {len(outcomes)} HITL outcomes.",
    ]
    themes: list[str] = []
    for o in edits:
        before = str(o.get("draft_before") or "")
        after = str(o.get("draft_after") or "")
        if not after or after == before:
            continue
        if len(after) < len(before) * 0.85:
            themes.append("humans shorten answers — prefer concise cited replies")
        if "[c" in after and "[c" not in before:
            themes.append("humans add citation markers")
        if "according to" in after.lower() and "according to" not in before.lower():
            themes.append("humans add explicit source attribution")
        if float(o.get("grounding_score") or 1) < 0.85:
            themes.append("low grounding scores correlate with HITL edits")
    seen: set[str] = set()
    for t in themes:
        if t not in seen:
            seen.add(t)
            summary.append(t)

    addendum = [
        "Prefer concise answers; every material claim must cite a chunk/doc_id.",
        "If evidence is thin, recommend HITL rather than inventing numbers.",
        "Never invent torque values, leave balances, SLAs, or change windows.",
    ]
    proposed = current.rstrip() + "\n\nAdditional guidance from recent HITL review:\n- "
    proposed += "\n- ".join(addendum)
    return {
        "summary": summary,
        "proposed_prompt": proposed,
        "rationale": "Heuristic proposal from edit/reject patterns (fake/offline path).",
    }


def propose_prompt(domain: str, outcomes: list[dict], current: str) -> dict:
    if not outcomes:
        return {
            "summary": ["No HITL outcomes found — nothing to refine."],
            "proposed_prompt": current,
            "rationale": "Empty log; returning the current prompt unchanged.",
        }
    if is_fake_chat_model(os.getenv("EGKP_MODEL", "fake")):
        return _heuristic_proposal(current, outcomes)
    try:
        llm = get_chat_model()
        reply = llm.invoke(
            [
                SystemMessage(content=REFINE_SYSTEM),
                HumanMessage(
                    content=REFINE_HUMAN.format(
                        domain=domain,
                        current_prompt=current,
                        n=len(outcomes),
                        outcomes_json=json.dumps(outcomes, ensure_ascii=False, indent=2)[:12000],
                    )
                ),
            ]
        )
        content = reply.content if isinstance(reply.content, str) else str(reply.content)
        parsed = _parse_proposal(content)
        if len(str(parsed.get("proposed_prompt") or "")) < 80:
            return _heuristic_proposal(current, outcomes)
        return parsed
    except Exception:
        return _heuristic_proposal(current, outcomes)


def next_version_label(domain: str) -> str:
    path = _ROOT / "data" / "prompts" / f"answerer_{domain}.json"
    if not path.exists():
        return "v2"
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        latest = str(doc.get("latest") or "v1")
        if latest.startswith("v") and latest[1:].isdigit():
            return f"v{int(latest[1:]) + 1}"
    except (json.JSONDecodeError, OSError, ValueError):
        pass
    return "v+1"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Propose a v+1 answerer procedural prompt from recent HITL edits."
    )
    parser.add_argument("--domain", default="manufacturing")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    args = parser.parse_args(argv)

    outcomes = load_hitl_outcomes(path=args.log, limit=args.limit)
    domain_rows = [o for o in outcomes if o.get("domain") in (None, args.domain)]
    rows = domain_rows if domain_rows else outcomes
    current = get_answerer_prompt(args.domain, version="latest")
    proposal = propose_prompt(args.domain, rows, current)
    version = next_version_label(args.domain)

    print("=" * 72)
    print(f"Answerer prompt refine proposal - domain={args.domain} -> {version}")
    print(f"HITL log: {args.log}  (using {len(rows)} of last {args.limit})")
    print("=" * 72)
    print("\n## Common HITL edit / reject patterns\n")
    for item in proposal.get("summary") or []:
        print(f"- {item}")
    print("\n## Rationale\n")
    print(proposal.get("rationale") or "(none)")
    print(f"\n## Proposed {version} prompt\n")
    print(proposal.get("proposed_prompt") or current)
    print("\n" + "=" * 72)
    print(
        "NOT APPLIED. Review above, then manually update "
        f"data/prompts/answerer_{args.domain}.json (or call set_answerer_prompt) if approved."
    )
    print("=" * 72)


if __name__ == "__main__":
    main()
