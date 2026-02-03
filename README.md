uv run uvicorn api.main:app --reload --port 8080
uv run python scripts/validate_kb.py
uv run --extra dev pytest

## Report Schema

The RCA report payload includes these top-level fields:
- `incident_summary`
- `time_range`
- `top_hypothesis`
- `other_hypotheses`
- `fallback_hypotheses`
- `evidence`
- `what_changed` (deploys/builds/changes)
- `impact_scope` (error signatures, event reasons, trace ids)
- `next_validations`

### Example Response
```json
{
  "incident_summary": "High error rate (severity=critical, env=prod)",
  "time_range": {
    "start": "2024-01-01T12:00:00Z",
    "end": "2024-01-01T12:10:00Z"
  },
  "top_hypothesis": {
    "id": "h1",
    "statement": "A deploy regression introduced a new error signature in the service.",
    "confidence": 0.78,
    "score_breakdown": {
      "coverage": 0.75,
      "temporal_alignment": 1.0,
      "kb_match": 1.0,
      "deploy_signal": 0.8,
      "specificity": 0.6,
      "contradiction_penalty": 0.0,
      "total": 0.78
    },
    "supporting_evidence_ids": ["logs_1", "deploy_1", "change_1"],
    "contradictions": [],
    "validations": ["Verify error signature appears after the deploy time window."]
  },
  "other_hypotheses": [],
  "fallback_hypotheses": [],
  "evidence": [
    {
      "id": "logs_1",
      "kind": "logs",
      "source": "log_store_1",
      "time_range": {"start": "2024-01-01T12:00:00Z", "end": "2024-01-01T12:10:00Z"},
      "query": "{app=\"payments\"}",
      "summary": "Top error signatures computed over the time window.",
      "samples": [],
      "top_signals": {"signatures": ["NullPointerException", "DB timeout"]},
      "pointers": [],
      "tags": ["logs", "signatures"]
    }
  ],
  "what_changed": {
    "deployments": [{"deployment_refs": ["run:1"]}],
    "builds": [],
    "changes": [{"merged_prs": [{"number": 42, "title": "Bump dependency"}]}]
  },
  "impact_scope": {
    "error_signatures": ["NullPointerException", "DB timeout"],
    "event_reasons": [],
    "trace_ids": []
  },
  "next_validations": ["Verify error signature appears after the deploy time window."]
}
```

## Tracing And Persistence

Optional JSONL tracing and in-memory graph persistence are available via settings:
- `TRACE_FILE` (path to JSONL file; when set, emits trace events)
- `ENABLE_PERSISTENCE` (`true`/`false`; when true, enables LangGraph in-memory persistence)

## Testing

Test tooling is managed via `uv` and lives in the optional `dev` dependency group.

### Install test dependencies
```bash
uv sync --extra dev
```

### Run the full test suite
```bash
uv run --extra dev pytest
```

### Run only unit tests
```bash
uv run --extra dev pytest tests/unit
```

### Run only integration tests
```bash
uv run --extra dev pytest tests/integration
```

### Notes
- Tests add the repo root to `sys.path` to allow imports like `core/`, `providers/`, and `api/`.
- Integration tests stub external providers and the LLM client; no network calls are made.
- If you update `kb/` or `catalog/`, also run:
```bash
uv run python scripts/validate_kb.py
```

flowchart TB
  subgraph A[Global Tool Schema]
    S1["catalog/schema.yaml<br/>Defines categories + operations + contracts"]
    S2["schemas/instances.schema.json<br/>Validates instances.yaml structure"]
    S3["schemas/subjects.schema.json<br/>Validates subjects.yaml structure"]
  end

  subgraph B[Environment Catalog]
    I1["catalog/instances.yaml<br/>Concrete provider instances<br/>(id, category, type, ops, config)"]
  end

  subgraph C[Customer Onboarding]
    K1["kb/subjects.yaml<br/>Subjects + bindings + selectors + knowledge"]
  end

  subgraph D[Agent Core]
    G1["LangGraph RCA Workflow<br/>capability-driven nodes<br/>(logs, deploys, changes)"]
    R1["ProviderRegistry<br/>resolves bindings + enforces ops"]
    L1["LLM Hypothesizer<br/>vendor-neutral prompts"]
    SC["Deterministic Scorer<br/>ranks hypotheses"]
  end

  subgraph E[Adapters / Providers]
    P1["log_store adapter(s)<br/>intent → backend query"]
    P2["deploy_tracker adapter(s)<br/>deploy history + metadata"]
    P3["vcs adapter(s)<br/>change history"]
  end

  S2 --> I1
  S3 --> K1
  S1 --> I1

  I1 --> R1
  K1 --> R1

  R1 --> G1
  G1 --> P1
  G1 --> P2
  G1 --> P3
  P1 --> G1
  P2 --> G1
  P3 --> G1

  G1 --> L1 --> SC --> G1
