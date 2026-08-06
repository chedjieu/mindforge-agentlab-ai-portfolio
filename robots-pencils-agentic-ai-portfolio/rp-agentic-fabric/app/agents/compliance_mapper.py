"""Compliance mapper — load policy pack → guardrail config."""

from __future__ import annotations

from pathlib import Path

import yaml

from app.state import EngagementState

PACKS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "policy_packs"

DEFAULTS: dict[str, dict] = {
    "edtech": {
        "vertical": "edtech",
        "regs": ["FERPA"],
        "tool_allowlist": [
            "hybrid_search",
            "lookup_entity",
            "traverse_relations",
            "sis_stub_read",
            "get_engagement_history",
        ],
        "retention_days": 2555,
        "hitl_required": False,
        "forbidden_topics": ["cross_tenant_lookup", "student_ssn_bulk_export"],
    },
    "healthcare": {
        "vertical": "healthcare",
        "regs": ["HIPAA", "SOC2"],
        "tool_allowlist": [
            "hybrid_search",
            "lookup_entity",
            "traverse_relations",
            "fhir_stub_read",
            "get_engagement_history",
        ],
        "retention_days": 2555,
        "hitl_required": True,
        "forbidden_topics": ["clinical_diagnosis_advice", "cross_tenant_lookup", "phi_bulk_export"],
    },
    "finserv": {
        "vertical": "finserv",
        "regs": ["GLBA", "SOC2"],
        "tool_allowlist": [
            "hybrid_search",
            "lookup_entity",
            "traverse_relations",
            "salesforce_stub_read",
            "get_engagement_history",
        ],
        "retention_days": 2555,
        "hitl_required": True,
        "forbidden_topics": ["unlicensed_financial_advice", "cross_tenant_lookup"],
    },
    "retail": {
        "vertical": "retail",
        "regs": ["PCI-lite"],
        "tool_allowlist": [
            "hybrid_search",
            "lookup_entity",
            "traverse_relations",
            "salesforce_stub_read",
            "get_engagement_history",
        ],
        "retention_days": 730,
        "hitl_required": False,
        "forbidden_topics": ["cross_tenant_lookup", "raw_pan_storage"],
    },
}


def load_policy_pack(vertical: str) -> dict:
    path = PACKS_DIR / f"{vertical}.yaml"
    if path.exists():
        with path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        base = dict(DEFAULTS.get(vertical, DEFAULTS["edtech"]))
        base.update(data)
        return base
    return dict(DEFAULTS.get(vertical, DEFAULTS["edtech"]))


def compliance_mapper_node(state: EngagementState) -> dict:
    vertical = state["vertical"] or "edtech"
    pack = load_policy_pack(vertical)
    pack_id = state.get("policy_pack_id") or f"{vertical}-v1"
    config = {
        **pack,
        "policy_pack_id": pack_id,
        "tenant_id": state["tenant_id"],
    }
    return {
        "guardrail_config": config,
        "policy_pack_id": pack_id,
        "step_log": state["step_log"]
        + [f"compliance_mapper: regs={config.get('regs')} allowlist={len(config.get('tool_allowlist', []))}"],
    }
