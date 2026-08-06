"""Generate sample PDFs for WOKA Phase 1."""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "sample_docs"

DOCS: list[tuple[str, str, list[str]]] = [
    (
        "01_se_dc_contingency_sop.pdf",
        "Southeast DC Contingency SOP",
        [
            "When ATL-01 or JAX-02 close, route demand to MEM-03 within 300 miles.",
            "Contracts with force-majeure alternate sourcing require 48h notice.",
            "Priority SKUs: MILK-GAL, WATER-24, TV-55-4K.",
        ],
    ),
    (
        "02_acme_vendor_contract.pdf",
        "Vendor Contract C-ACME-2024 - Acme Logistics",
        [
            "Supplier SUP-ACME serves Southeast electronics inbound.",
            "Alternate sourcing permitted with 48 hour written notice.",
            "Confidentiality: internal.",
        ],
    ),
    (
        "03_gulffresh_contract.pdf",
        "Vendor Contract C-GULF-2023 - GulfFresh Produce",
        [
            "Supplier SUP-GULF provides dairy and produce to JAX-02.",
            "Alternate sourcing permitted with 48 hour notice under force majeure.",
        ],
    ),
    (
        "04_inventory_policy.pdf",
        "Inventory Continuity Policy - Supply Chain",
        [
            "Stores projected under 50 units of perishable SKUs within 48h are stockout risks.",
            "Transfer from open DCs within 300 miles before emergency vendor buy.",
        ],
    ),
    (
        "05_hazardous_waste_sop.pdf",
        "Hazardous Waste Handling SOP - Store Ops",
        [
            "Managers must segregate hazardous waste and log Form HW-12 within 24 hours.",
            "California associates follow state addendum CA-HW-2024.",
        ],
    ),
    (
        "06_return_policy_us.pdf",
        "US Return Policy - Store Operations",
        [
            "Damaged merchandise may be returned within 30 days with manager approval.",
            "Receipt required for cash refunds over $25.",
        ],
    ),
    (
        "07_fda_recall_playbook.pdf",
        "FDA Contamination Recall Playbook",
        [
            "Identify affected SKUs, suppliers, DCs, and store on-hands within 4 hours.",
            "Produce executive action plan with shipment holds and customer notices.",
        ],
    ),
    (
        "08_payroll_ca_addendum.pdf",
        "California Payroll Policy Addendum",
        [
            "CA meal and rest break premiums apply to store associates.",
            "Overtime after 8 hours in a workday for non-exempt roles.",
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
        pdf.ln(1)
    pdf.output(str(path))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for filename, title, lines in DOCS:
        write_pdf(OUT / filename, title, lines)
    print(f"Generated {len(DOCS)} sample PDFs in {OUT}")


if __name__ == "__main__":
    main()
