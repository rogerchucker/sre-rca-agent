# SRE RCA Agent Tracker

## Original Ask (Condensed)
Build an SRE RCA agent using LangGraph + OpenAI. It accepts incidents/alerts via webhook, gathers temporal evidence (logs, deploy/build history, VCS changes) plus a static KB, correlates them, and returns ranked root-cause hypotheses. Demo flows should trigger real alerts and then reset, with the rest showing the agentic investigation.

## Current State (Repo Reality)
- **Agent Core**: LangGraph-oriented RCA workflow code lives in `core/` (orchestrator, prompts, scoring, registry).
- **Provider Abstractions**: Capability-based adapters in `providers/` for `log_store`, `deploy_tracker`, and `vcs`.
- **KB + Catalog**: Static onboarding via YAML in `kb/` and `catalog/`.
- **API Entry**: FastAPI app in `api/` (local run via `uvicorn api.main:app`).
- **Validation**: KB/catalog consistency check script at `scripts/validate_kb.py`.
- **Docs**: `docs/onboarding.md` includes onboarding guidance.
- **Tests**: Unit + integration tests exist under `tests/` and run via `uv run --extra dev pytest`.

## What Is Operational vs. Not Yet
### Operational (Local)
- Start the API locally.
- Edit `kb/subjects.yaml` and `catalog/instances.yaml`.
- Validate KB/catalog bindings.

### Missing to Be Operational End-to-End
1) **Webhook ingestion**
   - No explicit incident/alert webhook route defined with schema + auth.
2) **Provider implementations**
   - Adapters exist, but concrete integrations (Loki/CloudWatch/Splunk/kubectl; deploy/build systems; GitHub) are not wired end-to-end.
3) **Evidence timeframe binding**
   - No standard request model tying incident time window to provider queries.
4) **Correlation + ranking contract**
   - Hypothesis scoring exists, but the API response contract isn’t defined.
5) **Demo harness**
   - No scripts to induce alerts or reset states.
6) **Config management**
   - `.env`/secrets handling is implied but not documented or validated in run paths.
7) **Tests**
   - No automated tests or fixtures for adapters or workflows.

## Next Milestones
### M1: Webhook + Request Model
- [x] Define request schema for incident/alert input.
- [x] Add `/webhook/incident` endpoint with validation.
- [x] Map timeframe + subject selectors into the core workflow.

### M2: Evidence Adapters (MVP)
- Implement one `log_store` (e.g., Loki or CloudWatch).
- Implement one `deploy_tracker` (e.g., GitHub Actions or Argo).
- Implement one `vcs` (GitHub commits + diff summary).

### M3: RCA Output Contract
- Define API response for ranked hypotheses and confidence.
- Include evidence summary and citations in response.

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

## Open Questions
- Which provider stack should be the first supported path (Loki vs CloudWatch vs Splunk)?
- Which deploy history source should be MVP (GitHub Actions, Argo, Spinnaker, etc.)?
- What is the expected response format for hypotheses (JSON schema)?
- Do we need auth or signing for the webhook in MVP?
