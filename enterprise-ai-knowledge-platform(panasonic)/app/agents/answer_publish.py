"""Answer publish worker — audit log + optional quality Slack alert."""

from __future__ import annotations

import os

from app.state import KnowledgeState
from app.tools.notify_slack import notify_slack
from app.tools.publish_answer import publish_answer


def answer_publish_node(state: KnowledgeState) -> dict:
    approval = state.get("approval")
    if approval not in ("approved", "edited", "auto"):
        return {
            "step_log": state["step_log"]
            + [f"answer_publish: skipped (approval={approval})"],
        }

    draft = state.get("draft_answer") or {}
    answer = str(draft.get("answer") or "")
    grounding = state.get("grounding_score")
    threshold = float(os.getenv("GROUNDING_SHIP_THRESHOLD", "0.85"))

    publish_answer(
        thread_id=str(state.get("thread_id") or ""),
        domain=state.get("domain"),
        query=str(state.get("query") or ""),
        answer=answer,
        citations=list(state.get("citations") or []),
        grounding_score=grounding,
        approval=str(approval),
    )

    step_log = list(state["step_log"])
    step_log.append("answer_publish: wrote published_answers.log")

    if grounding is not None and grounding < threshold:
        notify_slack(
            "#egkp-quality",
            [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*EGKP low grounding* score=`{grounding:.2f}` "
                            f"(threshold `{threshold}`) domain=`{state.get('domain')}`\n"
                            f"Q: {state.get('query')}"
                        ),
                    },
                }
            ],
        )
        step_log.append(
            f"answer_publish: notified #egkp-quality (grounding={grounding:.2f}<{threshold})"
        )

    return {"published": True, "step_log": step_log}
