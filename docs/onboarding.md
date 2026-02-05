Mental checksum (use this every time you add a subject)

If you’re unsure whether something belongs in subjects.yaml, ask:

“Is this about who the subject is or how to find its data?”

	•	Yes → subjects.yaml
	•	No, it’s about how a tool works → global schema / adapter
	•	No, it’s about API endpoints or auth → provider instance config

Local environment

Use `.env.local` for local development. It is gitignored and loaded alongside `.env`.

Required for local persistence:
	•	ENABLE_PERSISTENCE="true"
	•	DATABASE_URL="postgresql://postgres:postgres@localhost:5432/rca_agent_db"

Other env vars should mirror `.env.example` (API keys, provider endpoints).
