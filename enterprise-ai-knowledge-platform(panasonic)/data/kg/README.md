# Knowledge graph seeds (`data/kg/`)

Aligned entity/relation seeds for Neo4j GraphRAG. Schema: [`docs/SYSTEM_DESIGN.md` §6](../../docs/SYSTEM_DESIGN.md#6-corpus--knowledge-graph-schema).

## Files (after corpus generator)

| File | Format | Minimum |
|------|--------|---------|
| `seed_entities.jsonl` | One entity JSON per line | ≥ 40 |
| `seed_relations.jsonl` | One edge JSON per line | ≥ 60 |

**Labels:** `Document`, `Section`, `Part`, `BOM`, `Plant`, `SOP`, `Policy`, `Role`, `TicketPattern`, `Service`, `Symptom`

**Rels:** `GOVERNS`, `APPLIES_TO`, `SUPERSEDES`, `LOCATED_AT`, `REQUIRES`, `PART_OF`, `REFERENCES`

Loaded idempotently by `app/ingest/pipeline.py` (`MERGE`). If Neo4j is unavailable, `graph_walker` may fall back to scanning these JSONL files in-process.
