"""WOKA graph state."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


def _merge_dicts(left: dict[str, Any] | None, right: dict[str, Any] | None) -> dict[str, Any]:
    return {**(left or {}), **(right or {})}


class WokaState(TypedDict, total=False):
    query: str
    user_id: str
    role: str
    department: str
    region: str
    scope: dict[str, Any]
    workers: list[str]
    blocked: bool
    block_reason: str
    worker_results: Annotated[dict[str, Any], _merge_dicts]
    retrieval: dict[str, Any]
    sql: dict[str, Any]
    internet: dict[str, Any]
    citations: list[dict[str, Any]]
    compliance: dict[str, Any]
    analytics: dict[str, Any]
    judges: dict[str, Any]
    audit_id: str
    answer: str
    confidence: float
    agents_used: Annotated[list[str], operator.add]
    step_log: Annotated[list[str], operator.add]
    final_response: str
