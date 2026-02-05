# Go-Live Tracker

## 1) Wire Real Providers (smallest viable)
1. Choose first target stack (e.g., Loki + GitHub Actions + kubectl).
2. Populate `catalog/instances.yaml` with real endpoints and auth env names.
3. Update `kb/subjects.yaml` with real services and bindings.
4. Run: `uv run python scripts/validate_kb.py`.

## 2) Start the API Locally
1. Set required env vars:
   - `OPENAI_API_KEY`
   - `LOG_STORE_URL`, `METRICS_URL`, `TRACE_URL` (if used)
   - `VCS_TOKEN`, `DEPLOY_TOKEN`, `BUILD_TOKEN` (as needed)
2. Launch: `uv run uvicorn api.main:app --reload --port 8080`.
3. Trigger a demo: `uv run python scripts/demo_trigger.py`.

## 3) Enable Persistence (for real ops)
1. Set `ENABLE_PERSISTENCE=true` and `DATABASE_URL=postgresql://…`.
2. Start once to auto-create tables (or add migrations later).
3. Verify `/incidents` and `/reports`.

## 4) Verify Evidence Flow
1. Send a webhook payload (Alertmanager or your tool).
2. Confirm it:
   - loads KB for the subject
   - executes evidence tools
   - produces `top_hypothesis` with supporting evidence IDs

## 5) Add Guardrails
1. Tighten tool limits in adapters (caps, time windows).
2. Add redaction and PII handling in log adapters.

## 6) Add Observability
1. Set `TRACE_FILE=/path/trace.jsonl` to capture runs.
2. Add request logging at the API boundary.
