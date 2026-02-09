# Onboarding

The onboarding workflow configures two YAML files:
- `catalog/instances.yaml`: provider instances (id, category, operations, config)
- `kb/subjects.yaml`: subjects (services) and their bindings to providers

The UI is the primary editing surface. Chat is optional and is constrained to propose and apply operations into the same form model.

## Profiles
Profiles control the initial seed loaded into the UI:
- `template` (default): vendor-neutral placeholders
- `demo`: seeded demo content (opt-in)

Backend env:
- `ONBOARDING_PROFILE=template|demo` (default `template`)
- `SHOW_DEMO_DATA=false` (demo incident widgets off by default)

Seed sources:
- Template: `catalog/seeds/template.instances.yaml`, `kb/seeds/template.subjects.yaml`
- Demo: `catalog/seeds/demo.instances.yaml`, `kb/seeds/demo.subjects.yaml`

## UI Flow
1. Edit providers, subjects, and bindings in `/onboarding`.
2. Click `Preview + Validate` to:
   - validate schema and bindings
   - render generated YAML
   - show diffs
3. Click `Apply changes` to write YAML with backups.

## API Endpoints
- `GET /knowledge/onboarding/model` (optional `?profile=template|demo`)
- `POST /knowledge/onboarding/model/preview`
- `POST /knowledge/onboarding/model/apply`
- `POST /knowledge/onboarding/agent/plan`
- `POST /knowledge/onboarding/agent/apply-ops`

## Schema Enforcement
Provider operations are validated against `catalog/rca-tools.schema.yaml` during preview/apply.

## CopilotKit
CopilotKit runtime routes live under the UI (`/copilotkit`) and call OpenAI.

Required env:
- `OPENAI_API_KEY`

Optional:
- `COPILOTKIT_MODEL` (defaults to `gpt-4o-mini`)

Local dev convenience:
- The UI server attempts to load the repo-root `.env.local` if `OPENAI_API_KEY` is not present in its environment.
