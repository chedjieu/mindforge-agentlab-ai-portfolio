# Demo corpus (`data/corpus/`)

NDA-safe enterprise documentation for RAG demos. Full schema and rationale: [`docs/SYSTEM_DESIGN.md` §6](../../docs/SYSTEM_DESIGN.md#6-corpus--knowledge-graph-schema).

## Layout (after `python -m scripts.generate_synthetic_corpus`)

```text
data/corpus/
  manufacturing/   # SOPs, plant safety — Part ↔ SOP ↔ Plant
  engineering/     # design standards — supersession chains
  support/         # KB + troubleshooting trees
  hr/              # policies — Role ↔ Policy (HITL required)
  operations/      # ITIL-style runbooks — Service ↔ runbook
```

Each markdown file must include YAML frontmatter: `doc_id`, `domain`, `doc_type`, `plant`, `acl_roles`, `effective_date`, `supersedes`, `entities`.

Do not commit proprietary Panasonic PDFs. Prefer the generator script over hand-scraped dumps.
