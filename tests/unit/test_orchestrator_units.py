from core.orchestrator import normalize_incident, seed_alert_evidence, score_and_report, _shift_rfc3339
from core.models import Hypothesis


def test_normalize_incident_time_buffer():
    payload = {
        "alerts": [
            {
                "labels": {"subject": "payments", "environment": "prod", "severity": "critical"},
                "annotations": {"summary": "High error rate"},
                "startsAt": "2024-01-01T12:00:00Z",
                "endsAt": "2024-01-01T12:10:00Z",
            }
        ]
    }
    state = {"raw_webhook": payload}
    out = normalize_incident(state)
    tr = out["incident"]["time_range"]
    assert tr["start"] == _shift_rfc3339("2024-01-01T12:00:00Z", -10)
    assert tr["end"] == "2024-01-01T12:10:00Z"


def test_seed_alert_evidence():
    state = {
        "incident": {
            "title": "t",
            "severity": "s",
            "environment": "prod",
            "subject": "payments",
            "time_range": {"start": "2024-01-01T12:00:00Z", "end": "2024-01-01T12:10:00Z"},
            "labels": {"k": "v"},
            "annotations": {"a": "b"},
            "raw": {},
        }
    }
    out = seed_alert_evidence(state)
    assert len(out["evidence"]) == 1
    assert out["evidence"][0]["kind"] == "alert"


def test_score_and_report_fallback():
    state = {
        "incident": {
            "title": "t",
            "severity": "s",
            "environment": "prod",
            "subject": "payments",
            "time_range": {"start": "2024-01-01T12:00:00Z", "end": "2024-01-01T12:10:00Z"},
            "labels": {},
            "annotations": {},
            "raw": {},
        },
        "evidence": [],
        "hypotheses": [],
    }

    out = score_and_report(state)
    report = out["report"]
    assert "Insufficient evidence" in report["top_hypothesis"]["statement"]
    assert report["top_hypothesis"]["confidence"] == 0.0


def test_normalize_incident_skips_when_present():
    state = {
        "incident": {
            "title": "t",
            "severity": "s",
            "environment": "prod",
            "subject": "payments",
            "time_range": {"start": "2024-01-01T12:00:00Z", "end": "2024-01-01T12:10:00Z"},
            "labels": {},
            "annotations": {},
            "raw": {},
        }
    }
    out = normalize_incident(state)
    assert out["incident"]["subject"] == "payments"
