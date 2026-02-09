# SRE RCA Agent

Vendor-neutral SRE investigation and root cause analysis (RCA) agent with schema-backed onboarding for evidence providers (logs, metrics, traces, deploy history, VCS, alerting).

## What You Get
- FastAPI backend for RCA workflows and onboarding endpoints.
- Provider adapters grouped by capability under `providers/`.
- Onboarding Studio UI that edits a model, previews diffs, validates, and only then writes `catalog/instances.yaml` and `kb/subjects.yaml`.
- Optional CopilotKit assistant that proposes onboarding operations and applies them only after confirmation.

## Repository Layout
- `api/`: FastAPI entrypoints (see `api/main.py`)
- `core/`: RCA workflow, registry, prompts, scoring, config
- `providers/`: adapter implementations grouped by capability
- `catalog/`: tool schema and provider instances (`catalog/instances.yaml`)
- `kb/`: subjects and bindings (`kb/subjects.yaml`)
- `scripts/`: utilities like YAML validation (`scripts/validate_kb.py`)
- `ui/`: SvelteKit onboarding UI + CopilotKit runtime route

## License
Apache-2.0. See `LICENSE`.

## Quickstart

### Backend (FastAPI)
1. Create `.env.local` in the repo root:
```bash
OPENAI_API_KEY=...
```
2. Run:
```bash
uv sync --extra dev
uv run uvicorn api.main:app --reload --port 8080
```

### Validate Onboarding YAML
```bash
uv run python scripts/validate_kb.py
```

### UI (Onboarding Studio)
1. Install deps:
```bash
cd ui
npm ci
```
2. Run UI:
```bash
npm run dev
```

CopilotKit runtime routes (`/copilotkit`) use `OPENAI_API_KEY`. For local dev, the UI server attempts to load the repo-root `.env.local`. You can also set `OPENAI_API_KEY` in `ui/.env.local` (see `ui/.env.example`).

## Onboarding Profiles
Onboarding supports:
- `template`: vendor-neutral placeholders (default)
- `demo`: seeded demo content (opt-in)

Backend:
- `ONBOARDING_PROFILE=template|demo` (default `template`)
- `SHOW_DEMO_DATA=false` by default

UI:
- Profile selector in `/onboarding` persists in `localStorage`

## Schema-Backed Validation
Provider operations declared in `catalog/instances.yaml` are validated against `catalog/rca-tools.schema.yaml` during preview/apply.

## Assistant Contract
The onboarding assistant does not write files. It:
1. Proposes an operation plan: `POST /knowledge/onboarding/agent/plan`
2. Applies accepted ops to the in-memory UI model: `POST /knowledge/onboarding/agent/apply-ops`
3. File writes happen only via `Preview + Validate` then `Apply changes`

## Testing
```bash
uv sync --extra dev
uv run --extra dev pytest
```
