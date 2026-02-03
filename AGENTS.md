# Repository Guidelines

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
