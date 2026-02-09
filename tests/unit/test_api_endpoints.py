from __future__ import annotations

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

import api.main as api
from core import db
from core.models import EvidenceItem, Hypothesis, RCAReport, TimeRange


def _reset_db_state():
    db.ENGINE = None
    db.SessionLocal = None


def _sample_report() -> RCAReport:
    tr = TimeRange(start="2024-01-01T00:00:00Z", end="2024-01-01T00:10:00Z")
    ev = EvidenceItem(
        id="e1",
        kind="log",
        source="test",
        time_range=tr,
        query="q",
        summary="s",
        samples=["line"],
        top_signals={"signatures": ["boom"]},
        pointers=[],
        tags=[],
    )
    hyp = Hypothesis(
        id="h1",
        statement="hyp",
        confidence=0.9,
        score_breakdown={"total": 0.9},
        supporting_evidence_ids=["e1"],
        contradictions=[],
        validations=["v1"],
    )
    return RCAReport(
        incident_summary="summary",
        time_range=tr,
        top_hypothesis=hyp,
        other_hypotheses=[],
        fallback_hypotheses=[],
        evidence=[ev],
        supporting_evidence=[],
        what_changed={},
        impact_scope={},
        next_validations=["v1"],
    )


def test_api_endpoints_no_persistence(monkeypatch):
    client = TestClient(api.app)

    monkeypatch.setattr(api, "persistence_enabled", lambda: False)
    api.LAST_REPORT = None
    monkeypatch.setattr(api, "run", lambda payload: {"ok": True})

    assert client.get("/health").json() == {"ok": True}
    assert "live_mode" in client.get("/ui/mode").json()

    resp = client.post("/webhook", json={"alerts": []})
    assert resp.status_code == 200

    report = _sample_report().model_dump()
    monkeypatch.setattr(api, "run_incident", lambda incident: report)

    payload = {
        "title": "t",
        "severity": "p1",
        "environment": "production",
        "subject": "svc",
    }
    resp = client.post("/webhook/incident", json=payload)
    assert resp.status_code == 200

    assert client.get("/ui/incidents").status_code == 200
    assert client.get("/ui/incidents/inc-current/timeline").status_code == 200
    assert client.get("/ui/incidents/inc-current/hypotheses").status_code == 200
    assert client.get("/ui/actions").status_code == 200
    assert client.get("/ui/summary").status_code == 200
    assert client.get("/ui/attention").status_code == 200
    assert client.get("/signals/timeline").status_code == 200
    assert client.get("/signals/correlation").status_code == 200
    assert client.get("/knowledge/runbooks").status_code == 200
    assert client.get("/knowledge/patterns").status_code == 200
    assert client.get("/knowledge/incidents").status_code == 200
    assert client.get("/knowledge/onboarding").status_code == 200

    assert client.get("/incidents").status_code == 503


def test_api_endpoints_with_persistence(monkeypatch):
    client = TestClient(api.app)

    class Row:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    tr = _sample_report().time_range
    incident = Row(
        id="inc-1",
        title="t",
        severity="p1",
        environment="prod",
        subject="svc",
        starts_at=datetime.fromisoformat(tr.start.replace("Z", "+00:00")),
        ends_at=datetime.fromisoformat(tr.end.replace("Z", "+00:00")),
        labels={},
        annotations={},
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    report_row = Row(
        id="rep-1",
        incident_id="inc-1",
        incident_summary="summary",
        report=_sample_report().model_dump(),
        created_at=datetime.now(timezone.utc),
    )
    action_exec = Row(id="exec-1", incident_id="inc-1", status="completed", payload={})
    audit = Row(id="aud-1", incident_id="inc-1", actor="system", action="x", detail={}, created_at=datetime.now(timezone.utc))

    class FakeResult:
        def __init__(self, rows):
            self._rows = rows

        def scalars(self):
            return self

        def first(self):
            return self._rows[0] if self._rows else None

        def all(self):
            return list(self._rows)

        def scalar_one(self):
            return len(self._rows)

    class FakeDB:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, stmt):
            sql = str(stmt)
            if "incident_reports" in sql:
                return FakeResult([report_row])
            if "audit_events" in sql:
                return FakeResult([audit])
            if "incidents" in sql:
                return FakeResult([incident])
            return FakeResult([])

        def get(self, model, obj_id):
            if obj_id == "inc-1":
                return incident
            if obj_id == "rep-1":
                return report_row
            if obj_id == "exec-1":
                return action_exec
            return None

    monkeypatch.setattr(api, "persistence_enabled", lambda: True)
    monkeypatch.setattr(api, "get_db", lambda: FakeDB())
    monkeypatch.setattr(api, "create_action_execution", lambda *a, **k: "exec-1")
    monkeypatch.setattr(api, "update_action_status", lambda *a, **k: None)
    monkeypatch.setattr(api, "record_audit", lambda *a, **k: None)

    assert client.get("/ui/summary").status_code == 200
    assert client.get("/ui/attention").status_code == 200
    assert client.get("/incidents").status_code == 200
    assert client.get("/incidents/inc-1").status_code == 200
    assert client.get("/incidents/inc-1/reports").status_code == 200
    assert client.get("/incidents/inc-1/reports/latest").status_code == 200
    assert client.get("/reports/rep-1").status_code == 200
    assert client.get("/incidents/inc-1/changes").status_code == 200
    assert client.get("/incidents/inc-1/alerts").status_code == 200

    action_payload = {"incident_id": "inc-1", "name": "check", "payload": {}}
    assert client.post("/actions/dry-run", json=action_payload).status_code == 200
    assert client.post("/actions/approve", json=action_payload).status_code == 200
    assert client.post("/actions/execute", json=action_payload).status_code == 200
    assert client.get("/actions/exec-1/status").status_code == 200
    assert client.get("/audit").status_code == 200
