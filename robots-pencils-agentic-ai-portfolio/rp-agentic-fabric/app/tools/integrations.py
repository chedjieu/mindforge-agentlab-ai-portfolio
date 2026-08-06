"""Mock integration connectors — always tenant-scoped."""

from __future__ import annotations


def sis_stub_read(tenant_id: str) -> dict:
    return {
        "system": "SIS/Banner",
        "tenant_id": tenant_id,
        "objects": ["Student", "Enrollment", "Term"],
        "notes": "FERPA-scoped read stub — no live SIS connection",
        "sample_fields": ["student_id", "program", "term_code"],
    }


def fhir_stub_read(tenant_id: str) -> dict:
    return {
        "system": "FHIR R4",
        "tenant_id": tenant_id,
        "resources": ["Patient", "Encounter", "Observation"],
        "notes": "HIPAA-scoped FHIR stub — no live EHR connection",
        "sample_fields": ["patient_id", "encounter_class", "status"],
    }


def salesforce_stub_read(tenant_id: str) -> dict:
    return {
        "system": "Salesforce",
        "tenant_id": tenant_id,
        "objects": ["Account", "Case", "Contact"],
        "notes": "CRM stub — credentials never cross tenant boundaries",
        "sample_fields": ["account_id", "case_number", "status"],
    }
