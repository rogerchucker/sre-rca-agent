# Onboarding Reset Architecture Note

## Why this reset
The onboarding experience was functional but hard to trust because:
- demo subject/provider content leaked into default UX,
- chat directly mutated local state without backend policy checks,
- transaction visibility was weak.

## What is now implemented

### 1) Profile-based onboarding seeds
- Default onboarding profile is `template`.
- Optional `demo` profile is explicit.
- Seeds:
  - `catalog/seeds/template.instances.yaml`
  - `kb/seeds/template.subjects.yaml`
  - `catalog/seeds/demo.instances.yaml`
  - `kb/seeds/demo.subjects.yaml`

### 2) Dedicated onboarding sub-agent API
- `POST /knowledge/onboarding/agent/plan`
  - input: `intent`, `model`, `policy`
  - output: `proposed_ops`, `preview_model`, `warnings`, `requires_confirmation`
- `POST /knowledge/onboarding/agent/apply-ops`
  - input: `model`, `ops`, `policy`
  - output: updated `model`, `warnings`, `applied_ops`, `rejected_ops`

Planner behavior is deterministic and policy-gated. It does not write files.

### 3) UI contract
- Forms remain source of truth.
- Chat proposes operations; user reviews and confirms in transaction panel.
- Accepted operations update visible form state.
- Persist still requires explicit `Preview + Validate` and `Apply changes`.

## Policy constraints currently enforced
- No invented provider IDs for bindings.
- Capability/category mismatch bindings are rejected when policy enforcement is enabled.
- Missing provider references are surfaced as warnings.

## Persistence model
- `agent/plan` and `agent/apply-ops` are model-only operations.
- Only `/knowledge/onboarding/model/apply` writes YAML files (with backups).

## Next iteration candidates
- Expand operation grammar (update/remove operations).
- Add richer domain-specific templates.
- Add deeper LLM planning for intents while preserving deterministic apply semantics.
