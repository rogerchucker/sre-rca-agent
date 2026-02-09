#!/usr/bin/env python3
"""
Reset local demo state.

In OSS, this is deliberately conservative. It does not attempt to delete any
real external resources. When persistence is enabled, it clears local DB tables.

Unit tests monkeypatch DB methods so this module must be import-safe.
"""

from __future__ import annotations

from core.config import settings
from core import db as core_db


def main() -> int:
    if not settings.enable_persistence:
        print("Persistence disabled; nothing to reset.")
        return 0

    # These functions are no-ops under unit tests via monkeypatching.
    core_db.init_db()
    with core_db.get_db() as session:
        # Best-effort truncate of known tables if available.
        # Import here to avoid heavy imports during module import.
        try:
            from core.persistence_models import Incident, EvidenceItem, IncidentReport, ActionExecution, AuditEvent

            for model in (AuditEvent, ActionExecution, EvidenceItem, IncidentReport, Incident):
                session.query(model).delete()
            session.commit()
        except Exception:
            # If models or session aren't available, don't fail hard for reset.
            pass

    print("Reset complete.")
    return 0


if __name__ == "__main__":
    # Intentionally do not raise SystemExit; unit tests execute this module via runpy.
    main()
