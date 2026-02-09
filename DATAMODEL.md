# Data Model

## Overview
The RCA agent uses a vendor-neutral data model to normalize incident input, evidence, hypotheses, and final reports. It separates:
- Runtime models (`core/models.py`) used during RCA flow
- Persistence models (`core/persistence_models.py`) used for storage
- Knowledge base (`kb/subjects.yaml`) and provider catalog (`catalog/instances.yaml`)

## Canonical Environments
All environments are canonicalized to one of:
- `prod`
- `staging`
- `dev`

Aliases are accepted and normalized:
- `production`, `prd` -> `prod`
- `stage`, `stg` -> `staging`
- `development` -> `dev`

Enforcement points:
- Webhook ingest (`core/orchestrator.normalize_incident`)
- API incident ingest (`api/main.py` -> `/webhook/incident`)
- KB subject lookup (`core/kb.py`)

Unknown or empty environment values raise `ValueError`.

## Runtime Models (core/models.py)

### IncidentInput
Vendor-neutral incident representation.
- `title`, `severity`, `environment`, `subject`
- `time_range: TimeRange`
- `labels`, `annotations`, `raw`

### TimeRange
- `start`, `end` (RFC3339 strings)

### EvidenceItem
Normalized evidence from any source.
- `kind` (canonical): `alert`, `log`, `metric`, `deployment`, `change`, `trace`, `event`, `build`, `service_graph`, `runbook`, `other`
- `source` (provider instance id)
- `time_range`, `query`, `summary`
- `samples`, `top_signals`, `pointers`, `tags`

### Hypothesis
- `statement`, `confidence`
- `supporting_evidence_ids`, `contradictions`, `validations`
- `score_breakdown`

### RCAReport
Final output:
- `top_hypothesis`, `other_hypotheses`, `fallback_hypotheses`
- `evidence`, `supporting_evidence`
- `what_changed`, `impact_scope`, `next_validations`

### Provider-neutral Query Requests
Typed request objects for adapter calls:
- `LogQueryRequest`, `DeployQueryRequest`, `ChangeQueryRequest`, `BuildQueryRequest`,
  `MetricsQueryRequest`, `TraceQueryRequest`, `EventQueryRequest`, `K8sLogQueryRequest`

## Persistence Models (core/persistence_models.py)

### Incident
- Stored with `starts_at`, `ends_at` as `DateTime(timezone=True)`

### IncidentReport
- Stores a serialized `RCAReport` payload (`report` JSON)

### EvidenceItem + Hypothesis
- Use **composite primary keys** `(incident_id, id)` to avoid collisions across incidents

### Action / ActionExecution / AuditEvent
- Track validation/mitigation actions and audit events

## Knowledge Base & Catalog

### KB (kb/subjects.yaml)
Per-subject configuration:
- `bindings` to provider instance IDs
- `log_evidence` parsing rules
- `known_failure_modes`, `runbooks`, `dependencies`

### Provider Catalog (catalog/instances.yaml)
Concrete tool instances and adapter configs. Loaded at runtime via `settings.catalog_path`.

## Notes
- Evidence kinds are aligned to the canonical taxonomy in `catalog/rca-tools.schema.yaml`.
- Environment canonicalization is enforced at ingest and lookup to prevent mismatches.
