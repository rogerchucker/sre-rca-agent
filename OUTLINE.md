# RCA Agent Outline (Implementation-Tracked)

## Goal
Build a vendor-neutral SRE investigation + RCA agent (LangGraph + OpenAI) that:
- ingests incident/alert webhooks,
- correlates temporal evidence + static onboarding knowledge,
- produces ranked hypotheses and one top recommendation.

## Current Implemented Scope

### Core workflow
- Webhook ingest and incident normalization are implemented in `api/main.py`.
- Evidence collection + hypothesis generation/scoring run via `core/orchestrator.py`.
- Read-only provider adapters exist under `providers/` by capability.

### Onboarding system
- Structured onboarding model endpoints are implemented:
  - `GET /knowledge/onboarding/model`
  - `POST /knowledge/onboarding/model/preview`
  - `POST /knowledge/onboarding/model/apply`
- YAML preview/diff/apply and resolved binding checks are implemented.

### Onboarding profiles (new)
- Profile-driven seeds are implemented:
  - `template`: `catalog/seeds/template.instances.yaml`, `kb/seeds/template.subjects.yaml`
  - `demo`: `catalog/seeds/demo.instances.yaml`, `kb/seeds/demo.subjects.yaml`
- `GET /knowledge/onboarding/model?profile=...` loads profile seeds.
- File persistence still only writes to configured real targets (`catalog/instances.yaml`, `kb/subjects.yaml`).

### Onboarding sub-agent (new)
- Dedicated backend planner/applicator endpoints are implemented:
  - `POST /knowledge/onboarding/agent/plan`
  - `POST /knowledge/onboarding/agent/apply-ops`
- Planner is deterministic (intent -> operations), applies policy gates, and never writes files.
- Binding policy checks enforce provider existence and capability/category compatibility.

### UI alignment (new)
- `/onboarding` now includes:
  - profile selector (`Template`, `Demo`) persisted to local storage,
  - assistant transaction panel (proposed/applied/rejected operations),
  - category-aware binding provider filtering,
  - inline JSON validation for provider config,
  - resolved binding severity labels (`OK`, `Unresolved Provider`, `Category Mismatch`) and unused provider warnings.

## Approved Exceptions / Deviations
1. Onboarding sub-agent implementation is deterministic rule-based currently.
- Reason: stronger reproducibility and policy control for onboarding mutations.
- Deferred option: move to deeper LangGraph planner for richer natural-language parsing.

2. Demo capability remains available but quarantined via explicit profile.
- Reason: preserve demo flow without polluting default onboarding experience.

## Deferred Items
- Broader multi-sub-agent orchestration for RCA runtime (beyond onboarding).
- Additional provider profile templates per platform stack.
- Richer onboarding intent grammar and operation types (update/delete/transform ops).
- Expanded integration/e2e coverage for onboarding assistant transaction behavior.

## Guardrails
- Core remains vendor-neutral by capability contracts.
- No direct file writes from onboarding planner/apply-ops endpoints.
- Persist only through `/knowledge/onboarding/model/apply` after validation.
