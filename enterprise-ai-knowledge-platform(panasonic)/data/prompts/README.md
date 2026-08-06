# Procedural memory prompts

Versioned answerer prompts written by Day 2 H3 of [`project-prompts.md`](../../project-prompts.md):

```text
answerer_{engineering,manufacturing,hr,support,operations}.json
```

Each file shape:

```json
{
  "domain": "manufacturing",
  "latest": "v1",
  "versions": {
    "v1": {
      "prompt": "You are an enterprise knowledge answerer...",
      "created_at": "2026-01-01T00:00:00Z"
    }
  }
}
```

Refine cron may propose `v+1` but must not auto-write without human review.
