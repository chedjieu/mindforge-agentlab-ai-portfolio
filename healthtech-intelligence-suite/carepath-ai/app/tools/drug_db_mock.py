"""Mock drug interaction + renal dosing database."""

from __future__ import annotations

from typing import Any

# Pairwise interactions (sorted pair keys looked up after sorting names)
INTERACTIONS: list[dict[str, Any]] = [
    {
        "pair": ["lisinopril", "potassium"],
        "severity": "moderate",
        "note": "ACEI + potassium — hyperkalemia risk; monitor K+",
    },
    {
        "pair": ["atorvastatin", "omeprazole"],
        "severity": "minor",
        "note": "Possible CYP interaction; usually clinically minor",
    },
    {
        "pair": ["metformin", "contrast"],
        "severity": "major",
        "note": "Hold metformin around iodinated contrast if eGFR reduced",
    },
    {
        "pair": ["aspirin", "lisinopril"],
        "severity": "minor",
        "note": "High-dose NSAID/ASA may blunt ACEI effect; low-dose ASA OK",
    },
    {
        "pair": ["amlodipine", "simvastatin"],
        "severity": "moderate",
        "note": "CCB may increase statin exposure — prefer atorvastatin limits",
    },
    {
        "pair": ["benzodiazepine", "opioid"],
        "severity": "major",
        "note": "Sedative synergy — respiratory depression risk",
    },
    {
        "pair": ["alprazolam", "tramadol"],
        "severity": "major",
        "note": "Sedative synergy — respiratory depression risk",
    },
    {
        "pair": ["alprazolam", "codeine"],
        "severity": "major",
        "note": "Sedative synergy — avoid co-prescribing when possible",
    },
    {
        "pair": ["sertraline", "tramadol"],
        "severity": "major",
        "note": "Serotonin syndrome risk",
    },
    {
        "pair": ["prednisone", "albuterol"],
        "severity": "minor",
        "note": "Monitor for hypokalemia with systemic steroids + beta-agonists",
    },
]

RENAL_RULES: list[dict[str, Any]] = [
    {
        "medication": "metformin",
        "egfr_max_full_dose": 60,
        "egfr_stop": 30,
        "note": "Reduce metformin dose when eGFR 30–45; stop if eGFR < 30",
    },
    {
        "medication": "gabapentin",
        "egfr_max_full_dose": 60,
        "egfr_stop": 15,
        "note": "Renally clear — adjust gabapentin for CKD",
    },
]


def check_interactions(meds: list[str]) -> list[dict[str, Any]]:
    normalized = [m.lower().strip() for m in meds if m]
    hits: list[dict[str, Any]] = []
    for rule in INTERACTIONS:
        a, b = rule["pair"]
        if a in normalized and b in normalized:
            hits.append({**rule, "source": "drug_db_mock"})
        # fuzzy: if rule med is substring of a prescribed med
        elif any(a in m for m in normalized) and any(b in m for m in normalized):
            hits.append({**rule, "source": "drug_db_mock"})
    # COPD/depression golden: alprazolam + any opioid-like
    if any("alprazolam" in m or "benzodiazepine" in m for m in normalized):
        if any(x in " ".join(normalized) for x in ("codeine", "tramadol", "oxycodone", "opioid")):
            if not any(h.get("pair") == ["alprazolam", "codeine"] for h in hits):
                hits.append(
                    {
                        "pair": ["alprazolam", "opioid"],
                        "severity": "major",
                        "note": "Sedative synergy — respiratory depression risk",
                        "source": "drug_db_mock",
                    }
                )
    return hits


def check_renal_adjustments(meds: list[str], labs: dict[str, Any]) -> list[dict[str, Any]]:
    egfr = labs.get("egfr") or labs.get("eGFR")
    try:
        egfr_f = float(egfr) if egfr is not None else None
    except (TypeError, ValueError):
        egfr_f = None
    if egfr_f is None:
        return []
    out: list[dict[str, Any]] = []
    med_l = [m.lower() for m in meds]
    for rule in RENAL_RULES:
        med = rule["medication"]
        if not any(med in m for m in med_l):
            continue
        if egfr_f < rule["egfr_stop"]:
            out.append({**rule, "action": "stop", "egfr": egfr_f})
        elif egfr_f < rule["egfr_max_full_dose"]:
            out.append({**rule, "action": "reduce", "egfr": egfr_f})
    return out
