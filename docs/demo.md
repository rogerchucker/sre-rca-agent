Demo flow

Trigger demo incident
- Run `uv run python scripts/demo_trigger.py`
- This posts a sample incident payload to `/webhook/incident`

Reset demo data
- Run `uv run python scripts/demo_reset.py`
- Clears incidents, reports, evidence, actions, and audit events from Postgres

Notes
- Requires `ENABLE_PERSISTENCE=true` and `DATABASE_URL` set in `.env.local`.
