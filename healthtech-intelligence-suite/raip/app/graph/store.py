"""Graph store: Neo4j when configured, else in-memory relationship plane."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class GraphEdge:
    rel: str
    src: str
    dst: str
    props: dict[str, Any] = field(default_factory=dict)


class GraphStore(Protocol):
    def upsert_document(
        self,
        *,
        tenant_id: str,
        document_id: str,
        title: str,
        version_id: str,
        version_number: str,
        authority_tier: str,
        supersedes_version_id: str | None = None,
    ) -> None: ...
    def upsert_chunk(
        self,
        *,
        tenant_id: str,
        document_id: str,
        version_id: str,
        chunk_id: str,
        section: str,
        page: int,
        injection_flagged: bool = False,
    ) -> None: ...
    def claim_evidence(self, tenant_id: str, claim_id: str, chunk_id: str, rel: str) -> None: ...
    def superseded_version_ids(self, tenant_id: str, version_id: str) -> set[str]: ...
    def neighbors(self, tenant_id: str, node_id: str, rel: str) -> list[str]: ...


class MemoryGraphStore:
    def __init__(self) -> None:
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: list[GraphEdge] = []

    def _key(self, tenant_id: str, node_id: str) -> str:
        return f"{tenant_id}:{node_id}"

    def upsert_document(
        self,
        *,
        tenant_id: str,
        document_id: str,
        title: str,
        version_id: str,
        version_number: str,
        authority_tier: str,
        supersedes_version_id: str | None = None,
    ) -> None:
        self.nodes[self._key(tenant_id, document_id)] = {
            "type": "Document",
            "title": title,
            "tenant_id": tenant_id,
            "authority_tier": authority_tier,
        }
        self.nodes[self._key(tenant_id, version_id)] = {
            "type": "Version",
            "version_number": version_number,
            "document_id": document_id,
            "tenant_id": tenant_id,
        }
        self.edges.append(GraphEdge("DOCUMENT_HAS_VERSION", document_id, version_id, {"tenant_id": tenant_id}))
        if supersedes_version_id:
            self.edges.append(
                GraphEdge(
                    "DOCUMENT_SUPERSEDES_DOCUMENT",
                    version_id,
                    supersedes_version_id,
                    {"tenant_id": tenant_id},
                )
            )

    def upsert_chunk(
        self,
        *,
        tenant_id: str,
        document_id: str,
        version_id: str,
        chunk_id: str,
        section: str,
        page: int,
        injection_flagged: bool = False,
    ) -> None:
        self.nodes[self._key(tenant_id, chunk_id)] = {
            "type": "Chunk",
            "section": section,
            "page": page,
            "tenant_id": tenant_id,
            "injection_flagged": injection_flagged,
        }
        self.edges.append(
            GraphEdge("SECTION_CONTAINS_CHUNK", version_id, chunk_id, {"tenant_id": tenant_id, "section": section})
        )

    def claim_evidence(self, tenant_id: str, claim_id: str, chunk_id: str, rel: str) -> None:
        self.edges.append(GraphEdge(rel, claim_id, chunk_id, {"tenant_id": tenant_id}))

    def superseded_version_ids(self, tenant_id: str, version_id: str) -> set[str]:
        out: set[str] = set()
        frontier = [version_id]
        while frontier:
            cur = frontier.pop()
            for e in self.edges:
                if e.rel == "DOCUMENT_SUPERSEDES_DOCUMENT" and e.src == cur and e.props.get("tenant_id") == tenant_id:
                    if e.dst not in out:
                        out.add(e.dst)
                        frontier.append(e.dst)
        return out

    def neighbors(self, tenant_id: str, node_id: str, rel: str) -> list[str]:
        return [
            e.dst
            for e in self.edges
            if e.rel == rel and e.src == node_id and e.props.get("tenant_id") == tenant_id
        ]


class Neo4jGraphStore:
    def __init__(self, uri: str, user: str, password: str) -> None:
        from neo4j import GraphDatabase

        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self._memory = MemoryGraphStore()

    def upsert_document(self, **kwargs: Any) -> None:
        self._memory.upsert_document(**kwargs)
        with self._driver.session() as session:
            session.run(
                """
                MERGE (d:Document {id: $document_id, tenant_id: $tenant_id})
                SET d.title = $title, d.authority_tier = $authority_tier
                MERGE (v:Version {id: $version_id, tenant_id: $tenant_id})
                SET v.version_number = $version_number
                MERGE (d)-[:DOCUMENT_HAS_VERSION]->(v)
                """,
                **kwargs,
            )
            if kwargs.get("supersedes_version_id"):
                session.run(
                    """
                    MATCH (v:Version {id: $version_id, tenant_id: $tenant_id})
                    MERGE (old:Version {id: $supersedes_version_id, tenant_id: $tenant_id})
                    MERGE (v)-[:DOCUMENT_SUPERSEDES_DOCUMENT]->(old)
                    """,
                    **kwargs,
                )

    def upsert_chunk(self, **kwargs: Any) -> None:
        self._memory.upsert_chunk(**kwargs)
        with self._driver.session() as session:
            session.run(
                """
                MATCH (v:Version {id: $version_id, tenant_id: $tenant_id})
                MERGE (c:Chunk {id: $chunk_id, tenant_id: $tenant_id})
                SET c.section = $section, c.page = $page, c.injection_flagged = $injection_flagged
                MERGE (v)-[:SECTION_CONTAINS_CHUNK]->(c)
                """,
                **kwargs,
            )

    def claim_evidence(self, tenant_id: str, claim_id: str, chunk_id: str, rel: str) -> None:
        self._memory.claim_evidence(tenant_id, claim_id, chunk_id, rel)
        safe = rel if rel in {"CLAIM_SUPPORTED_BY", "CLAIM_CONTRADICTED_BY"} else "CLAIM_SUPPORTED_BY"
        with self._driver.session() as session:
            session.run(
                f"""
                MERGE (cl:Claim {{id: $claim_id, tenant_id: $tenant_id}})
                MERGE (c:Chunk {{id: $chunk_id, tenant_id: $tenant_id}})
                MERGE (cl)-[:{safe}]->(c)
                """,
                tenant_id=tenant_id,
                claim_id=claim_id,
                chunk_id=chunk_id,
            )

    def superseded_version_ids(self, tenant_id: str, version_id: str) -> set[str]:
        return self._memory.superseded_version_ids(tenant_id, version_id)

    def neighbors(self, tenant_id: str, node_id: str, rel: str) -> list[str]:
        return self._memory.neighbors(tenant_id, node_id, rel)


_STORE: GraphStore | None = None


def graph_store() -> GraphStore:
    global _STORE
    if _STORE is None:
        uri = os.getenv("NEO4J_URI", "").strip()
        created: GraphStore
        if uri:
            try:
                created = Neo4jGraphStore(
                    uri,
                    os.getenv("NEO4J_USER", "neo4j"),
                    os.getenv("NEO4J_PASSWORD", "changeme"),
                )
            except Exception:
                created = MemoryGraphStore()
        else:
            created = MemoryGraphStore()
        _STORE = created
    return _STORE


def reset_graph_store() -> None:
    global _STORE
    _STORE = None
