from app.config import get_settings
from app.retrieval.hybrid import retrieve
from app.storage.db import get_session_factory
from app.storage.repo import Store


def test_ingest_seeded_chunks_have_pages() -> None:
    settings = get_settings()
    factory = get_session_factory()
    with factory() as session:
        store = Store(session, settings.demo_tenant)
        project = f"{settings.demo_tenant}-proj-golden"
        chunks = store.chunks_for_project(project)
        assert chunks
        assert all(c.page_number >= 1 for c in chunks)
        assert all(c.tenant_id == settings.demo_tenant for c in chunks)


def test_hybrid_retrieval_finds_metformin() -> None:
    settings = get_settings()
    tenant = settings.demo_tenant
    project = f"{tenant}-proj-golden"
    factory = get_session_factory()
    with factory() as session:
        store = Store(session, tenant)
        chunks = store.chunks_for_project(project)
        docs = {d.id: d for d in store.list_documents(project)}
        versions = {}
        for d in docs.values():
            for v in store.versions_for(d.id):
                versions[v.id] = v
    hits = retrieve("metformin first-line type 2 diabetes", chunks, docs, versions, tenant_id=tenant)
    assert hits
    assert any("metformin" in h.text.lower() for h in hits)
