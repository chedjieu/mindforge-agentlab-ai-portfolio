from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


def _merge_dicts(a: dict[str, Any] | None, b: dict[str, Any] | None) -> dict[str, Any]:
    out = dict(a or {})
    out.update(b or {})
    return out


def _extend_list(a: list[Any] | None, b: list[Any] | None) -> list[Any]:
    return list(a or []) + list(b or [])


class AssociateState(TypedDict, total=False):
    associate_id: str
    abac: dict[str, Any]
    query: str
    policy_pack: dict[str, Any]
    intents: list[str]
    workers: list[str]
    worker_results: Annotated[dict[str, Any], _merge_dicts]
    evidence: Annotated[list[dict[str, Any]], _extend_list]
    draft_response: str
    citations: list[dict[str, Any]]
    proposed_actions: list[dict[str, Any]]
    judges: dict[str, Any]
    approval: dict[str, Any] | None
    ticket_ids: list[str]
    final_response: str
    step_log: Annotated[list[str], operator.add]
    blocked: bool
    block_reason: str
    next: str
