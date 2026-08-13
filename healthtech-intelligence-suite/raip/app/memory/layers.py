"""Procedural / episodic / semantic memory with tenant boundaries."""

from __future__ import annotations

from typing import Any

import yaml

from app.config import ROOT


def procedural_policies() -> dict[str, Any]:
    path = ROOT / "sample_data" / "policies" / "authoring.yaml"
    if not path.exists():
        return {
            "no_fabrication": True,
            "evidence_only": True,
            "citation_required": True,
        }
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def episodic_examples(tenant_id: str) -> list[str]:
    path = ROOT / "sample_data" / "memory" / f"{tenant_id}-approved.txt"
    if path.exists():
        return [path.read_text(encoding="utf-8")[:1500]]
    fallback = ROOT / "sample_data" / "templates" / "approved_section.txt"
    if fallback.exists():
        return [fallback.read_text(encoding="utf-8")[:1500]]
    return []


def semantic_glossary(tenant_id: str) -> dict[str, str]:
    _ = tenant_id
    return {
        "T2DM": "type 2 diabetes mellitus",
        "first-line": "preferred initial pharmacologic therapy in the cited guideline",
    }
