from app.config import get_settings
from app.retrieval.hybrid import retrieve
from app.storage.db import get_session_factory
from app.storage.repo import Store


def test_northstar_cannot_retrieve_other_tenant_secret() -> None:
    settings = get_settings()
    factory = get_session_factory()
    with factory() as session:
        store = Store(session, settings.demo_tenant)
        project = f"{settings.demo_tenant}-proj-golden"
        chunks = store.chunks_for_project(project)
        docs = {d.id: d for d in store.list_documents(project)}
        versions = {}
        for d in docs.values():
            for v in store.versions_for(d.id):
                versions[v.id] = v
        hits = retrieve("SECRET TOKEN TENANT-OTHER", chunks, docs, versions, tenant_id=settings.demo_tenant)
        assert all("SECRET TOKEN" not in h.text for h in hits)
        other = Store(session, "tenant-other")
        other_chunks = other.chunks_for_tenant()
        assert any("SECRET TOKEN" in c.text for c in other_chunks)
