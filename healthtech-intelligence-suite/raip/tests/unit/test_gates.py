from app.models.contracts import ClaimRecord, SupportStatus
from app.safety.gates import run_gates


def test_critical_overrides_high_score() -> None:
    claims = [
        ClaimRecord(
            claim_id="CLM-1",
            claim="Give the patient 500 mg of DrugZ immediately.",
            claim_type="recommendation",
            risk_level="high",
            support_status=SupportStatus.UNSUPPORTED,
        )
    ]
    _, scores = run_gates(
        "Give the patient 500 mg of DrugZ immediately. Quality looks excellent.",
        claims,
        {"grounding": 0.97, "citation": 0.99, "coverage": 0.98, "unsupported_rate": 1.0},
    )
    assert scores.critical_safety_failure
    assert scores.publication_blocked
    assert scores.decision == "BLOCKED"
