"""Tenant-scoped repositories. Every query includes tenant_id."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.storage.schema import (
    AuditEventRow,
    DocumentRow,
    DocumentVersionRow,
    DraftRow,
    EvidenceChunkRow,
    ProjectRow,
    TemplateRow,
    TenantRow,
    UserRow,
)


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


class Store:
    def __init__(self, session: Session, tenant_id: str) -> None:
        self.s = session
        self.tenant_id = tenant_id

    def audit(
        self,
        action: str,
        request_id: str,
        actor_id: str,
        resource_type: str = "",
        resource_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.s.add(
            AuditEventRow(
                id=new_id("aud"),
                tenant_id=self.tenant_id,
                request_id=request_id,
                actor_id=actor_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                payload=json.dumps(metadata or {}, default=str)[:4000],
            )
        )

    def get_project(self, project_id: str) -> ProjectRow | None:
        return self.s.scalar(
            select(ProjectRow).where(
                ProjectRow.id == project_id, ProjectRow.tenant_id == self.tenant_id
            )
        )

    def list_projects(self) -> list[ProjectRow]:
        return list(
            self.s.scalars(select(ProjectRow).where(ProjectRow.tenant_id == self.tenant_id)).all()
        )

    def list_documents(self, project_id: str | None = None) -> list[DocumentRow]:
        q = select(DocumentRow).where(DocumentRow.tenant_id == self.tenant_id)
        if project_id:
            q = q.where(DocumentRow.project_id == project_id)
        return list(self.s.scalars(q).all())

    def get_document(self, document_id: str) -> DocumentRow | None:
        return self.s.scalar(
            select(DocumentRow).where(
                DocumentRow.id == document_id, DocumentRow.tenant_id == self.tenant_id
            )
        )

    def versions_for(self, document_id: str) -> list[DocumentVersionRow]:
        return list(
            self.s.scalars(
                select(DocumentVersionRow).where(
                    DocumentVersionRow.tenant_id == self.tenant_id,
                    DocumentVersionRow.document_id == document_id,
                )
            ).all()
        )

    def get_version(self, version_id: str) -> DocumentVersionRow | None:
        return self.s.scalar(
            select(DocumentVersionRow).where(
                DocumentVersionRow.id == version_id,
                DocumentVersionRow.tenant_id == self.tenant_id,
            )
        )

    def chunks_for_tenant(self) -> list[EvidenceChunkRow]:
        return list(
            self.s.scalars(
                select(EvidenceChunkRow).where(EvidenceChunkRow.tenant_id == self.tenant_id)
            ).all()
        )

    def chunks_for_project(self, project_id: str) -> list[EvidenceChunkRow]:
        docs = self.list_documents(project_id)
        ids = {d.id for d in docs}
        if not ids:
            return []
        return [
            c
            for c in self.chunks_for_tenant()
            if c.document_id in ids
        ]

    def get_draft(self, draft_id: str) -> DraftRow | None:
        return self.s.scalar(
            select(DraftRow).where(DraftRow.id == draft_id, DraftRow.tenant_id == self.tenant_id)
        )

    def draft_by_thread(self, thread_id: str) -> DraftRow | None:
        return self.s.scalar(
            select(DraftRow).where(
                DraftRow.thread_id == thread_id, DraftRow.tenant_id == self.tenant_id
            )
        )

    def list_drafts(self, project_id: str | None = None) -> list[DraftRow]:
        q = select(DraftRow).where(DraftRow.tenant_id == self.tenant_id)
        if project_id:
            q = q.where(DraftRow.project_id == project_id)
        return list(self.s.scalars(q.order_by(DraftRow.created_at.desc())).all())

    def audit_for_request(self, request_id: str) -> list[AuditEventRow]:
        return list(
            self.s.scalars(
                select(AuditEventRow)
                .where(
                    AuditEventRow.tenant_id == self.tenant_id,
                    AuditEventRow.request_id == request_id,
                )
                .order_by(AuditEventRow.created_at.asc())
            ).all()
        )


def ensure_tenant(session: Session, tenant_id: str, name: str) -> TenantRow:
    row = session.get(TenantRow, tenant_id)
    if row:
        return row
    row = TenantRow(id=tenant_id, name=name)
    session.add(row)
    return row


def ensure_user(session: Session, user_id: str, tenant_id: str, role: str, email: str) -> UserRow:
    row = session.get(UserRow, user_id)
    if row:
        return row
    row = UserRow(id=user_id, tenant_id=tenant_id, role=role, email=email)
    session.add(row)
    return row


def ensure_template(session: Session, tenant_id: str) -> TemplateRow:
    tid = f"{tenant_id}-tpl-clinical-mgmt"
    row = session.get(TemplateRow, tid)
    if row:
        return row
    row = TemplateRow(
        id=tid,
        tenant_id=tenant_id,
        name="Clinical Management Recommendations",
        required_sections=json.dumps(
            [
                "Purpose",
                "Clinical Management Recommendations",
                "Monitoring",
                "Limitations",
                "References",
            ]
        ),
        style_rules=json.dumps(
            {"citation_style": "numbered", "no_patient_specific_dosing": True}
        ),
    )
    session.add(row)
    return row


def utcnow_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"
