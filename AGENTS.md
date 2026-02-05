# Original Ask

I want to build an SRE agent from the ground up using Langgraph with OpenAI that focuses only one type of workflow -- investigations and root cause analysis. The input can be an incident or an alert reaching the agent through a standard webhook. Investigations require two types of information to start with —  evidence from temporal sources (telemetry, build and deployment history, change history which includes github commits) and pre-exisitng knowledge-base (i.e. dependency graphs, runbooks, association between tool category and actual tool being used, documentation on how the tool is being used, root causes of past incidents, feature documentation, etc.). The knowledge-base is what we onboard through the onboarding process (for now let’s limit that to the static one time configuration YAML file.

The evidence should collected from the logging infrastructure if applicable — this could mean querying Loki logs if the underlying stack uses Loki, or cloudwatch., or Splunk. This could also mean kubectll logs and kubectl events.  Other evidence sources can be build history and logs, code commits history and change details, deployment history. 

The evidence collected (within a timeframe matching the alert or the incident) along with the aforementioned knowledgebase should be sent for correlation and come up with root cause hypotheses. The recommendation coming back from the LLM should the one for the hypotheses with the highest confidence level.

The demo scenarios (both live and doks demos and in general) should be simply about deliberately triggering external systems into a state that trigger their corresponding alerts and also about deliberately reseting these changes. The rest of the demo flows should be the actual agentic flow as we described above.

The core of this tool should not refer to any specific tool or platform or vendor. I also don't want references to applications (like hn-feed or hn-backend-demo etc) in the core. Please show all the code of the core and the adapters accordingly including the new project structure

# Review Outline

Always review @OUTLINE.md to ensure the project is not deviating. If it is, call out the drifts and if approved by me, update @OUTLINE.md as exceptions in the corresponding sections.

# Repository Guidelines

## Rules for feature implementation
-  After every UI-related task completion, verify the changes as well as if this change regressed on  the actual UI by using the Playwroght skills.
- If something is broken, do not stop until you have fixed it.

## Project Structure & Module Organization
- `api/`: FastAPI entrypoints (see `api/main.py`).
- `core/`: RCA workflow, registry, prompts, scoring, and config.
- `providers/`: Adapter implementations grouped by capability (`log_store/`, `deploy_tracker/`, `vcs/`).
- `catalog/`: Global tool schemas and provider instances (e.g., `catalog/instances.yaml`).
- `kb/`: Subject definitions and examples (e.g., `kb/subjects.yaml`).
- `scripts/`: Utility scripts such as KB validation (`scripts/validate_kb.py`).
- `docs/`: Lightweight project notes (see `docs/onboarding.md`).

## Build, Test, and Development Commands
This repo uses `uv` for dependency management and running tools.
- `uv run uvicorn api.main:app --reload --port 8080`: start the API locally.
- `uv run python scripts/validate_kb.py`: validate `kb/subjects.yaml` against `catalog/instances.yaml`.

## Coding Style & Naming Conventions
- Python: 4-space indentation, PEP 8 style, `snake_case` for functions/vars, `PascalCase` for classes.
- Modules: keep capability-specific logic under `core/` and provider adapters under `providers/`.
- YAML keys: use lower_snake_case and keep provider IDs stable (referenced by `kb/subjects.yaml`).

## Testing Guidelines
- No automated test suite is currently present.
- Use `scripts/validate_kb.py` when modifying `kb/` or `catalog/` data.
- If you add tests, place them under a new `tests/` directory and document how to run them here.

## Commit & Pull Request Guidelines
- There is no established commit message convention yet (repository has no commits).
- Use short, imperative messages (e.g., `Add subject binding checks`).
- PRs should include:
  - A clear summary of changes and rationale.
  - Validation steps (e.g., `uv run python scripts/validate_kb.py`).
  - Updated docs if schemas, providers, or KB structure change.

## Security & Configuration Tips
- Avoid hardcoding credentials in `catalog/instances.yaml` or `kb/` files.
- Prefer environment variables and `.env` loading via the existing config utilities in `core/`.
