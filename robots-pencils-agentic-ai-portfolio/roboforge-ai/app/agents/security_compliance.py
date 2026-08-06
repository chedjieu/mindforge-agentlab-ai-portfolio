"""Security & compliance mapper."""

from __future__ import annotations

from app.state import ForgeState


def security_compliance_node(state: ForgeState) -> dict:
    domain = state.get("domain") or "agentic"
    intake = state.get("intake") or {}
    estate = state.get("estate") or {}
    findings = {
        "controls_checked": ["IAM least privilege", "Encryption at rest", "Secrets Manager", "OWASP LLM"],
        "gaps": [],
        "regs": [],
        "severity_max": "medium",
    }
    text = str(intake) + str(state.get("raw_pack"))
    low = text.lower()
    if "hipaa" in low or "phi" in low or "healthcare" in low:
        findings["regs"].append("HIPAA")
        findings["gaps"].append("BAAs and PHI tokenization path required")
        findings["severity_max"] = "high"
    if "pci" in low or "payment" in low:
        findings["regs"].append("PCI")
        findings["gaps"].append("No raw PAN in agent memory")
        findings["severity_max"] = "high"
    if "ferpa" in low or "student" in low:
        findings["regs"].append("FERPA")
    if not findings["regs"]:
        findings["regs"].append("SOC2")
    if estate.get("modernization_score", 1) < 0.45:
        findings["gaps"].append("Legacy blast radius — staged strangler migration")
        findings["severity_max"] = "high"
    findings["domain"] = domain
    findings["pass_preliminary"] = findings["severity_max"] != "critical"
    return {
        "security_findings": findings,
        "step_log": state["step_log"]
        + [f"security_compliance: regs={findings['regs']} severity={findings['severity_max']}"],
    }
