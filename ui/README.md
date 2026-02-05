# Operations Portal UI

SvelteKit + Tailwind CSS UI for the SRE Operations Portal.

## Run

```bash
uv run --directory ui npm install
uv run --directory ui npm run dev
```

The UI proxies API calls to `http://localhost:${BACKEND_PORT}` via `/api/*`.
Set `BACKEND_PORT` in `.env` or `.env.local` (defaults to `8080`).

## Pages

- `/` Command / Home
- `/signals` Signals Explorer
- `/incident` Incident / Investigation View
- `/action` Action Center
- `/knowledge` Knowledge & History
