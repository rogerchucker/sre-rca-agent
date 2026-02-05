from __future__ import annotations

import os

from core.persistence import persistence_enabled
from core.db import get_db, init_db
from core.persistence_models import Action, ActionExecution, AuditEvent, EvidenceItem, Hypothesis, Incident, IncidentReport

if not persistence_enabled():
    raise SystemExit("Persistence disabled. Set ENABLE_PERSISTENCE=true and DATABASE_URL.")

init_db()
with get_db() as db:
    db.query(ActionExecution).delete()
    db.query(AuditEvent).delete()
    db.query(Action).delete()
    db.query(Hypothesis).delete()
    db.query(EvidenceItem).delete()
    db.query(IncidentReport).delete()
    db.query(Incident).delete()

print("Demo data cleared.")
