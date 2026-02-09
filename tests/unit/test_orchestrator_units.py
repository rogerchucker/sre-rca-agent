from core.orchestrator import normalize_incident, seed_alert_evidence, score_and_report, summarize_evidence, _shift_rfc3339
from core.models import EvidenceItem, TimeRange


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
    assert "what_changed" in report
    assert "impact_scope" in report
    assert "fallback_hypotheses" in report
    assert "supporting_evidence" in report


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


def test_score_and_report_sets_iteration_flag_for_low_confidence():
    tr = TimeRange(start="2024-01-01T12:00:00Z", end="2024-01-01T12:10:00Z")
    state = {
        "incident": {
            "title": "t",
            "severity": "s",
            "environment": "prod",
            "subject": "payments",
            "time_range": tr.model_dump(),
            "labels": {},
            "annotations": {},
            "raw": {},
        },
        "evidence": [],
        "hypotheses": [
            {
                "id": "h1",
                "statement": "Minor issue.",
                "confidence": 0.0,
                "score_breakdown": {},
                "supporting_evidence_ids": [],
                "contradictions": [],
                "validations": [],
            }
        ],
        "iteration": 0,
    }

    out = score_and_report(state)
    assert out["should_iterate"] is True
    assert out["iteration"] == 1


def test_score_and_report_stops_when_confident():
    tr = TimeRange(start="2024-01-01T12:00:00Z", end="2024-01-01T12:10:00Z")
    evidence = [
        EvidenceItem(
            id="e_logs",
            kind="log",
            source="s1",
            time_range=tr,
            query="q",
            summary="s",
        ),
        EvidenceItem(
            id="e_deploy",
            kind="deployment",
            source="s2",
            time_range=tr,
            query="q",
            summary="s",
            top_signals={"deployment_refs": ["run:1"]},
        ),
        EvidenceItem(
            id="e_change",
            kind="change",
            source="s3",
            time_range=tr,
            query="q",
            summary="s",
        ),
    ]
    state = {
        "incident": {
            "title": "t",
            "severity": "s",
            "environment": "prod",
            "subject": "payments",
            "time_range": tr.model_dump(),
            "labels": {},
            "annotations": {},
            "raw": {},
        },
        "kb_slice": {
            "subject_cfg": {
                "known_failure_modes": [
                    {"name": "deploy_regression", "indicators": ["deploy related regression"]}
                ]
            }
        },
        "evidence": [e.model_dump() for e in evidence],
        "hypotheses": [
            {
                "id": "h1",
                "statement": "This is a sufficiently long hypothesis statement about deploy related regression.",
                "confidence": 0.0,
                "score_breakdown": {},
                "supporting_evidence_ids": ["e_logs", "e_deploy", "e_change"],
                "contradictions": [],
                "validations": [],
            }
        ],
        "iteration": 1,
    }

    out = score_and_report(state)
    assert out["should_iterate"] is False
    assert out["iteration"] == 1
    report = out["report"]
    assert any(line.startswith("- [") for line in report["supporting_evidence"])


def test_summarize_evidence_adds_kb_items():
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
        "kb_slice": {
            "subject_cfg": {
                "name": "payments",
                "dependencies": [{"name": "postgres", "role": "primary"}],
                "runbooks": [{"title": "DB pool troubleshooting", "link": "https://example.invalid"}],
            }
        },
        "evidence": [],
    }

    out = summarize_evidence(state)
    kinds = {e["kind"] for e in out["evidence"]}
    assert "service_graph" in kinds
    assert "runbook" in kinds
    graph = next(e for e in out["evidence"] if e["kind"] == "service_graph")["top_signals"]["graph"]
    assert graph["nodes"][0]["id"] == "payments"
    assert graph["edges"][0]["to"] == "postgres"
