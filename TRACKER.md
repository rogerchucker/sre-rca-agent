# SRE RCA Agent Tracker

## Original Ask (Condensed)
Build an SRE RCA agent using LangGraph + OpenAI. It accepts incidents/alerts via webhook, gathers temporal evidence (logs, deploy/build history, VCS changes) plus a static KB, correlates them, and returns ranked root-cause hypotheses. Demo flows should trigger real alerts and then reset, with the rest showing the agentic investigation.

## Current State (Repo Reality)
- **Agent Core**: LangGraph-oriented RCA workflow code lives in `core/` (orchestrator, prompts, scoring, registry).
- **Provider Abstractions**: Capability-based adapters in `providers/` for `log_store`, `deploy_tracker`, `build_tracker`, `runtime` (kubectl), `metrics_store`, `trace_store`, and `vcs`.
- **KB + Catalog**: Static onboarding via YAML in `kb/` and `catalog/` with bindings for logs, deploys, builds, runtime, metrics, traces, and VCS.
- **API Entry**: FastAPI app in `api/` (local run via `uvicorn api.main:app`).
- **Validation**: KB/catalog consistency check script at `scripts/validate_kb.py`.
- **Docs**: `docs/onboarding.md` includes onboarding guidance.
- **Tests**: Unit + integration tests exist under `tests/` and run via `uv run --extra dev pytest` (passing).

## What Is Operational vs. Not Yet
### Operational (Local)
- Start the API locally.
- Edit `kb/subjects.yaml` and `catalog/instances.yaml`.
- Validate KB/catalog bindings.
- Run tests (unit + integration).

### Missing to Be Operational End-to-End
1) **SummarizeEvidence + KB evidence items**
   - No dedicated summarize node; service-graph/runbook evidence items not emitted.
2) **Structured hypothesis outputs**
   - Hypotheses still parsed from raw JSON response (not structured outputs/tool-calling).
3) **Scoring coverage gaps**
   - Temporal alignment, KB match, and new evidence types not scored yet.
4) **Persistence/tracing hooks**
   - No optional LangGraph persistence or tracing/eval harness.
5) **Report schema gaps**
   - RCAReport missing explicit “impact scope” and “what changed” sections.
6) **Demo harness**
   - No scripts to induce alerts or reset states.
7) **Config management**
   - `.env`/secrets handling is implied but not documented or validated in run paths.

## Next Milestones
### M1: Webhook + Request Model
- [x] Define request schema for incident/alert input.
- [x] Add `/webhook/incident` endpoint with validation.
- [x] Map timeframe + subject selectors into the core workflow.

### M2: Evidence Adapters (MVP)
- [x] Implement one `log_store` (Loki).
- [x] Implement one `deploy_tracker` (GitHub Actions).
- [x] Implement one `build_tracker` (GitHub Actions).
- [x] Implement one `runtime` (kubectl logs/events).
- [x] Implement one `metrics_store` (Prometheus).
- [x] Implement one `trace_store` (Jaeger).
- [x] Implement one `vcs` (GitHub changes).

### M3: RCA Output Contract
- [x] Define API response for ranked hypotheses and confidence.
- [x] Include evidence summary and citations in response.

### M4: Demo Scenarios
- Scripted alert trigger + rollback for at least one live and one DOKS demo.
- Document runbook for demo flow.

## Operational Checklist (Local)
- [ ] `uv sync`
- [ ] `uv run uvicorn api.main:app --reload --port 8080`
- [ ] Define webhook endpoint + request schema
- [ ] Implement and configure at least one provider per capability
- [ ] Validate KB/catalog with `uv run python scripts/validate_kb.py`
- [ ] Run an end-to-end RCA call against a real incident payload
- [ ] Run tests with `uv run --extra dev pytest`

## In-Flight Tasks (Ordered)
1) [x] Add SummarizeEvidence node and emit service-graph/runbook evidence items. (Tests: `uv run --extra dev pytest -q`)
2) [x] Upgrade hypotheses to structured outputs/tool-calling. (Tests: `uv run --extra dev pytest -q`)
3) [x] Extend scoring to include temporal alignment + KB match + additional evidence types. (Tests: `uv run --extra dev pytest -q`)
4) [x] Add optional persistence/tracing hooks. (Tests: `uv run --extra dev pytest -q`)
5) [x] Expand RCAReport schema to match the recommended output format. (Tests: `uv run --extra dev pytest -q`)

## Open Questions
- Which provider stack should be the first supported path (Loki vs CloudWatch vs Splunk)?
- Which deploy history source should be MVP (GitHub Actions, Argo, Spinnaker, etc.)?
- What is the expected response format for hypotheses (JSON schema)?
- Do we need auth or signing for the webhook in MVP?
