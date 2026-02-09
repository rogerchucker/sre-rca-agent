from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core.config import settings
from core import db
from core.persistence import (
    persistence_enabled,
    bootstrap,
    save_report,
    create_action_execution,
    update_action_status,
    record_audit,
    _parse_rfc3339,
)
from core.models import IncidentInput, TimeRange, EvidenceItem, Hypothesis, RCAReport


def _reset_db_state():
    db.ENGINE = None
    db.SessionLocal = None


def _sample_report() -> RCAReport:
    tr = TimeRange(start="2024-01-01T00:00:00Z", end="2024-01-01T00:10:00Z")
    evidence = [
        EvidenceItem(
            id="e1",
            kind="log",
            source="test",
            time_range=tr,
            query="q",
            summary="s",
            samples=[],
            top_signals={},
            pointers=[],
            tags=[],
        )
    ]
    top = Hypothesis(
        id="h1",
        statement="hyp",
        confidence=0.5,
        score_breakdown={"total": 0.5},
        supporting_evidence_ids=["e1"],
        contradictions=[],
        validations=["v1"],
    )
    return RCAReport(
        incident_summary="summary",
        time_range=tr,
        top_hypothesis=top,
        other_hypotheses=[],
        fallback_hypotheses=[],
        evidence=evidence,
        supporting_evidence=[],
        what_changed={},
        impact_scope={},
        next_validations=["v1"],
    )


def test_persistence_disabled(monkeypatch):
    monkeypatch.setattr(settings, "enable_persistence", False)
    monkeypatch.setattr(settings, "database_url", None)
    assert persistence_enabled() is False
    bootstrap()
    assert _parse_rfc3339("") is not None


def test_persistence_enabled_and_save_report(monkeypatch):
    monkeypatch.setattr(settings, "enable_persistence", True)
    monkeypatch.setattr(settings, "database_url", "postgresql://example.invalid/db")
    monkeypatch.setattr(db, "init_db", lambda: None)

    tr = TimeRange(start="2024-01-01T00:00:00Z", end="2024-01-01T00:10:00Z")
    incident = IncidentInput(
        title="t",
        severity="p1",
        environment="prod",
        subject="svc",
        time_range=tr,
        labels={},
        annotations={},
        raw={},
    )
    report = _sample_report()
    fake = FakeDB()
    monkeypatch.setattr("core.persistence.get_db", fake.ctx)
    incident_id = save_report(incident, report)
    assert incident_id is not None

    exec_id = create_action_execution(incident_id, "validate", {"k": "v"}, status="pending")
    assert exec_id

    update_action_status(exec_id, "completed", {"result": "ok"})
    record_audit("action.complete", incident_id=incident_id, detail={"id": exec_id})


class FakeDB:
    def __init__(self):
        self.rows = {}

    def ctx(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def add(self, row):
        if getattr(row, "id", None) is None:
            row.id = f"id-{len(self.rows) + 1}"
        self.rows[row.id] = row
        return None

    def flush(self):
        return None

    def get(self, _model, _id):
        return self.rows.get(_id)

    def commit(self):
        return None

    def rollback(self):
        return None

    def close(self):
        return None
