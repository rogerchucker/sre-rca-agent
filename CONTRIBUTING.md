# Contributing

Thanks for helping improve this project.

## Development Setup

### Backend (FastAPI)
- Install deps: `uv sync --extra dev`
- Run API: `uv run uvicorn api.main:app --reload --port 8080`
- Run tests: `uv run --extra dev pytest`

### UI (SvelteKit)
- Install deps: `cd ui && npm ci`
- Run UI: `cd ui && npm run dev`

CopilotKit server routes (`/copilotkit`) need `OPENAI_API_KEY` available to the UI server process.

## Repository Conventions
- Prefer vendor-neutral defaults in `catalog/instances.yaml` and `kb/subjects.yaml`. Put demos behind the onboarding profile toggle.
- File writes should go through the onboarding apply endpoint (with backups) and never directly from an assistant runtime.

## Pull Requests
- Include a clear description of behavior change and validation steps.
- Ensure `uv run --extra dev pytest` passes.
- If you changed onboarding UI, include a screenshot or Playwright snapshot where possible.
