"""Case loader + formulary helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "data" / "cases"


def load_case(domain: str, case_id: str) -> dict[str, Any]:
    path = CASES / domain / f"{case_id}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    # try folder layout
    folder = CASES / domain / case_id
    if folder.exists():
        payload: dict[str, Any] = {"case_id": case_id, "domain": domain}
        for f in folder.glob("*"):
            if f.suffix == ".json":
                payload[f.stem] = json.loads(f.read_text(encoding="utf-8"))
            elif f.suffix in {".md", ".txt"}:
                payload[f.stem] = f.read_text(encoding="utf-8")
        return payload
    return {"case_id": case_id, "domain": domain, "query": f"Handle {domain} case {case_id}"}


def list_cases(domain: str | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    domains = [domain] if domain else [p.name for p in CASES.iterdir() if p.is_dir()]
    for d in domains:
        folder = CASES / d
        if not folder.exists():
            continue
        for path in sorted(folder.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            out.append(
                {
                    "domain": d,
                    "case_id": data.get("case_id") or path.stem,
                    "title": data.get("title") or path.stem,
                    "summary": data.get("summary") or "",
                }
            )
    return out


FORMULARY = {
    "adalimumab": {"tier": 3, "step_therapy": ["methotrexate"], "preferred_alt": "preferred-adalimumab-biosimilar"},
    "mri_lumbar": {"requires": ["failed_conservative_care_6w"], "cpt": "72148"},
}


def formulary_check(drug_or_service: str) -> dict[str, Any]:
    key = (drug_or_service or "").lower().replace(" ", "_")
    for k, v in FORMULARY.items():
        if k in key or key in k:
            return {"item": k, **v}
    return {"item": drug_or_service, "tier": 2, "step_therapy": [], "note": "no special formulary rule"}
