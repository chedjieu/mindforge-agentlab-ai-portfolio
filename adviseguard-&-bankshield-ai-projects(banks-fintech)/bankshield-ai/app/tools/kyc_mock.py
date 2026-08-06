"""Mock KYC / identity verification tools (Alloy/Socure/Plaid stand-ins)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
KYC_PATH = ROOT / "data" / "alerts" / "kyc_profiles.json"


def _load_profiles() -> dict[str, Any]:
    if not KYC_PATH.exists():
        return {}
    data = json.loads(KYC_PATH.read_text(encoding="utf-8"))
    return {p["customer_id"]: p for p in data.get("profiles", [])}


def verify_identity(customer_id: str) -> dict[str, Any]:
    profiles = _load_profiles()
    profile = profiles.get(customer_id)
    if not profile:
        return {
            "customer_id": customer_id,
            "kyc_status": "unknown",
            "synthetic_risk": 0.4,
            "face_match": None,
            "findings": ["No KYC profile found in mock store"],
        }
    findings = list(profile.get("findings") or [])
    return {
        "customer_id": customer_id,
        "kyc_status": profile.get("kyc_status", "verified"),
        "synthetic_risk": float(profile.get("synthetic_risk", 0.1)),
        "face_match": profile.get("face_match"),
        "device_fingerprint": profile.get("device_fingerprint"),
        "account_age_days": profile.get("account_age_days"),
        "findings": findings,
        "name": profile.get("name"),
        "ofac_hit": bool(profile.get("ofac_hit", False)),
    }


def check_sanctions(name: str, country: str | None = None) -> dict[str, Any]:
    """Fixture OFAC/sanctions screening."""
    feeds = ROOT / "data" / "corpus" / "ofac_guidance" / "fixture_sdn_hits.md"
    text = feeds.read_text(encoding="utf-8") if feeds.exists() else ""
    low = (name or "").lower()
    hit = False
    matched = None
    for marker in ("vladimir petroski", "shelltrade ltd", "northhaven crypto"):
        if marker in low or (marker.split()[0] in low and "sanction" in text.lower()):
            # Near-match heuristics for demo sanctions case
            if any(part in low for part in marker.split()):
                hit = True
                matched = marker.title()
                break
    # Explicit profile flag path
    if "petrov" in low or "petroski" in low or "shelltrade" in low:
        hit = True
        matched = matched or name
    return {
        "name": name,
        "country": country,
        "ofac_match": hit,
        "matched_entry": matched,
        "list": "OFAC SDN (fixture)",
        "confidence": 0.92 if hit else 0.05,
    }
