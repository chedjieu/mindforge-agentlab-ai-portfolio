"""Generate 10 sample Walmart-themed PDFs for local dev."""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "sample_pdfs"

DOCS: list[tuple[str, str, list[str]]] = [
    (
        "01_us_return_policy.pdf",
        "US Return Policy - Store Operations",
        [
            "Damaged merchandise may be returned within 30 days with manager approval.",
            "Receipt required for cash refunds over $25.",
            "Canada stores follow regional addendum CAN-RET-2024.",
        ],
    ),
    (
        "02_supply_chain_sop.pdf",
        "Supply Chain SOP - Inbound Receiving",
        [
            "All inbound pallets must be scanned within 4 hours of dock arrival.",
            "Temperature-controlled items require probe verification at 38F or below.",
            "Q3 2024 supply-chain capex was $1.2B per finance table 4.2.",
        ],
    ),
    (
        "03_fcpa_training.pdf",
        "FCPA Training Requirements",
        [
            "All managers must complete annual FCPA certification by March 31.",
            "Third-party vendor due diligence is mandatory for contracts over $50,000.",
        ],
    ),
    (
        "04_vendor_sla_acme.pdf",
        "Vendor SLA - Acme Logistics",
        [
            "Acme guarantees 98.5% on-time delivery for domestic routes.",
            "Penalty clause: 2% credit per missed SLA window.",
        ],
    ),
    (
        "05_vendor_sla_beta.pdf",
        "Vendor SLA - Beta Freight",
        [
            "Beta guarantees 97.0% on-time delivery.",
            "Penalty clause: 1.5% credit per missed SLA window.",
        ],
    ),
    (
        "06_pharmacy_compliance.pdf",
        "Pharmacy Compliance - Controlled Substances",
        [
            "DEA Form 106 required within 24 hours for significant loss.",
            "Dual-count verification required for Schedule II inventory.",
        ],
    ),
    (
        "07_finance_q3_report.pdf",
        "Finance - Q3 2024 Summary",
        [
            "Revenue: $169.6B. Operating income: $6.7B.",
            "Supply-chain capex: $1.2B (see table 4.2).",
            "E-commerce growth: 22% YoY.",
        ],
    ),
    (
        "08_canada_regional_addendum.pdf",
        "Canada Regional Addendum - Returns",
        [
            "Canadian customers have 45-day return window for non-perishables.",
            "Bilingual signage required in Quebec locations.",
        ],
    ),
    (
        "09_data_retention_policy.pdf",
        "Data Retention Policy - IT Security",
        [
            "Employee records retained 7 years post-termination.",
            "Audit logs retained 3 years minimum.",
        ],
    ),
    (
        "10_executive_comp_summary.pdf",
        "Executive Compensation Summary - CONFIDENTIAL",
        [
            "Restricted to executive and board roles.",
            "CEO total compensation FY2024: $25.3M (salary + equity + bonus).",
        ],
    ),
]


def write_pdf(path: Path, title: str, lines: list[str]) -> None:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    width = pdf.epw
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(width, 8, title)
    pdf.ln(4)
    pdf.set_font("Helvetica", size=11)
    for line in lines:
        pdf.multi_cell(width, 6, f"- {line}")
    pdf.output(str(path))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for filename, title, lines in DOCS:
        write_pdf(OUT / filename, title, lines)
    print(f"Generated {len(DOCS)} sample PDFs in {OUT}")


if __name__ == "__main__":
    main()
