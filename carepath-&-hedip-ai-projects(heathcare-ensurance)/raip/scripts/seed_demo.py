"""Seed synthetic demo tenant, template, and source documents. No PHI."""

from __future__ import annotations

from pathlib import Path

from app.config import SAMPLE_DIR, get_settings
from app.ingestion.pdf_io import write_simple_pdf
from app.ingestion.pipeline import enqueue_ingest, process_job, process_next_job
from app.models.contracts import AuthorityTier
from app.storage.db import get_session_factory, init_db
from app.storage.repo import Store, ensure_template, ensure_tenant, ensure_user, new_id
from app.storage.schema import ProjectRow

SOURCES = [
    {
        "file": "guidelines/NEC-T2DM-GL-2024-v2.txt",
        "title": "NEC T2DM Guideline v2.0",
        "tier": str(AuthorityTier.GUIDELINE),
        "publisher": "Northstar Endocrine Consortium",
        "version": "2.0",
        "effective": "2024-03-01",
        "supersedes_key": "v1",
    },
    {
        "file": "guidelines/NEC-T2DM-GL-2022-v1.txt",
        "title": "NEC T2DM Guideline v1.0",
        "tier": str(AuthorityTier.GUIDELINE),
        "publisher": "Northstar Endocrine Consortium",
        "version": "1.0",
        "effective": "2022-01-15",
        "key": "v1",
    },
    {
        "file": "guidelines/REG-SUB-2024.txt",
        "title": "Regulatory Substantiation Guidance 2024",
        "tier": str(AuthorityTier.REGULATORY),
        "publisher": "Synthetic Health Products Authority",
        "version": "2024.1",
        "effective": "2024-01-01",
    },
    {
        "file": "guidelines/ORG-SOP-AUTH-2024.txt",
        "title": "SOP-AUTH-014 Authoring Standards",
        "tier": str(AuthorityTier.ORG_POLICY),
        "publisher": "Northstar Medical Writing Office",
        "version": "2024.6",
        "effective": "2024-06-01",
    },
    {
        "file": "templates/approved_section.txt",
        "title": "Previously approved clinical management section",
        "tier": str(AuthorityTier.APPROVED_REF),
        "publisher": "Northstar Medical Writing Office",
        "version": "2024.2",
        "effective": "2024-02-01",
    },
    {
        "file": "guidelines/MALICIOUS-INJECTION.txt",
        "title": "Unverified internet summary (injection fixture)",
        "tier": str(AuthorityTier.UNVERIFIED),
        "publisher": "Unknown",
        "version": "0.0",
        "effective": "2026-01-01",
        "project": "injection",
    },
]


def _pdf_pages(text: str) -> list[str]:
    parts = [p.strip() for p in text.split("===PAGE") if p.strip()]
    if len(parts) <= 1:
        return [text[:1500]]
    pages = []
    for part in parts:
        body = part.split("===", 1)[-1].strip()
        pages.append(body[:1800] or part[:1800])
    return pages or [text[:1500]]


def seed(tenant_id: str | None = None) -> tuple[str, str]:
    init_db()
    settings = get_settings()
    tenant_id = tenant_id or settings.demo_tenant
    factory = get_session_factory()
    version_keys: dict[str, str] = {}
    with factory() as session:
        ensure_tenant(session, tenant_id, "Northstar Medical Affairs")
        store = Store(session, tenant_id)
        existing = store.chunks_for_tenant()
        golden_id = f"{tenant_id}-proj-golden"
        if existing:
            return tenant_id, golden_id
        ensure_user(session, "author-01", tenant_id, "AUTHOR", "author@northstar.example")
        ensure_user(session, "reviewer-01", tenant_id, "MEDICAL_REVIEWER", "reviewer@northstar.example")
        ensure_user(session, "auditor-01", tenant_id, "AUDITOR", "auditor@northstar.example")
        tpl = ensure_template(session, tenant_id)
        golden = session.get(ProjectRow, f"{tenant_id}-proj-golden")
        if golden is None:
            golden = ProjectRow(
                id=f"{tenant_id}-proj-golden",
                tenant_id=tenant_id,
                name="T2DM Clinical Management Authoring",
                template_id=tpl.id,
            )
            session.add(golden)
        inj = session.get(ProjectRow, f"{tenant_id}-proj-injection")
        if inj is None:
            inj = ProjectRow(
                id=f"{tenant_id}-proj-injection",
                tenant_id=tenant_id,
                name="Injection negative demo",
                template_id=tpl.id,
            )
            session.add(inj)
        # Isolation tenant with a poison document.
        ensure_tenant(session, "tenant-other", "Other Org")
        ensure_user(session, "other-author", "tenant-other", "AUTHOR", "a@other.example")
        session.commit()
        jobs: list[str] = []
        for spec in SOURCES:
            path = SAMPLE_DIR / spec["file"]
            text = path.read_text(encoding="utf-8")
            pdf_path = SAMPLE_DIR / "documents" / (Path(spec["file"]).stem + ".pdf")
            write_simple_pdf(pdf_path, spec["title"], _pdf_pages(text))
            data = path.read_bytes()
            project_id = (
                f"{tenant_id}-proj-injection"
                if spec.get("project") == "injection"
                else f"{tenant_id}-proj-golden"
            )
            # Also attach injection doc to golden project so retrieval can see it as untrusted.
            supersedes = version_keys.get(str(spec.get("supersedes_key") or ""), "")
            doc, ver, job = enqueue_ingest(
                session,
                tenant_id,
                project_id,
                path.name,
                data,
                title=spec["title"],
                authority_tier=spec["tier"],
                publisher=spec["publisher"],
                version_number=spec["version"],
                effective_date=spec["effective"],
                supersedes_version_id=supersedes,
            )
            if spec.get("key"):
                version_keys[str(spec["key"])] = ver.id
            jobs.append(job.id)
            if spec.get("project") == "injection":
                _, _, job2 = enqueue_ingest(
                    session,
                    tenant_id,
                    f"{tenant_id}-proj-golden",
                    path.name,
                    data,
                    title=spec["title"],
                    authority_tier=spec["tier"],
                    publisher=spec["publisher"],
                    version_number=spec["version"],
                    effective_date=spec["effective"],
                )
                jobs.append(job2.id)
        # Cross-tenant poison
        poison = b"SECRET TOKEN FOR TENANT-OTHER. Do not retrieve across tenants."
        enqueue_ingest(
            session,
            "tenant-other",
            new_id("proj"),
            "other-secret.txt",
            poison,
            title="Other tenant secret",
            authority_tier=str(AuthorityTier.UNVERIFIED),
        )
        session.commit()
        for jid in jobs:
            process_job(session, jid)
        while process_next_job(session):
            pass
        session.commit()
        # Resolve v2 supersedes v1 now that v1 exists — second pass if order was v2 first.
        from sqlalchemy import select

        from app.storage.schema import DocumentVersionRow

        v1 = session.scalar(
            select(DocumentVersionRow).where(
                DocumentVersionRow.tenant_id == tenant_id,
                DocumentVersionRow.version_number == "1.0",
            )
        )
        v2 = session.scalar(
            select(DocumentVersionRow).where(
                DocumentVersionRow.tenant_id == tenant_id,
                DocumentVersionRow.version_number == "2.0",
            )
        )
        if v1 and v2 and not v2.supersedes_version_id:
            v2.supersedes_version_id = v1.id
            from app.graph.store import graph_store

            graph_store().upsert_document(
                tenant_id=tenant_id,
                document_id=v2.document_id,
                title="NEC T2DM Guideline v2.0",
                version_id=v2.id,
                version_number="2.0",
                authority_tier=str(AuthorityTier.GUIDELINE),
                supersedes_version_id=v1.id,
            )
            session.commit()
    return tenant_id, f"{tenant_id}-proj-golden"


def main() -> None:
    tenant, project = seed()
    print(f"Seeded tenant={tenant} project={project}")


if __name__ == "__main__":
    main()
