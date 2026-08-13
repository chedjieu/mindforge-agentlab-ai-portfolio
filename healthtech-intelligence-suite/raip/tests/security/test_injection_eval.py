from app.security.injection import scan_text, user_input_should_block
from security.injection_eval import ATTACKS, run


def test_suite_meets_threshold() -> None:
    assert run() == 0


def test_fifty_attacks_defined() -> None:
    assert len(ATTACKS) >= 50


def test_pdf_injection_fixture_flagged() -> None:
    text = open("sample_data/guidelines/MALICIOUS-INJECTION.txt", encoding="utf-8").read()
    assert scan_text(text).flagged
    assert not user_input_should_block("Draft the clinical management section from approved guidelines.")
