# Operations Portal UI

SvelteKit + Tailwind CSS UI for the SRE Operations Portal.

## Run

```bash
cd ui
npm ci
npm run dev
```

The UI proxies API calls to `http://localhost:${BACKEND_PORT}` via `/api/*`.
Set `BACKEND_PORT` in `.env` or `.env.local` (defaults to `8080`).
Set `OPENAI_API_KEY` for the CopilotKit onboarding assistant (`/copilotkit`).
For local dev, the UI server will also try to load the repo-root `.env.local` if the key is not set in the UI process environment.
Optional: set `COPILOTKIT_MODEL` (defaults to `gpt-4o-mini`).

## Pages

- `/` Command / Home
- `/signals` Signals Explorer
- `/incident` Incident / Investigation View
- `/action` Action Center
- `/knowledge` Knowledge & History
- `/onboarding` YAML Onboarding Studio
