from fastapi.testclient import TestClient

from api.main import app


def test_health():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_webhook_calls_orchestrator(monkeypatch):
    client = TestClient(app)

    def fake_run(payload):
        return {"incident_summary": "ok", "top_hypothesis": {"id": "h1"}}

    monkeypatch.setattr("api.main.run", fake_run)

    resp = client.post("/webhook", json={"a": 1})
    assert resp.status_code == 200
    assert resp.json()["incident_summary"] == "ok"


def test_webhook_incident(monkeypatch):
    client = TestClient(app)

    def fake_run_incident(incident):
        return {"incident_summary": "incident ok", "top_hypothesis": {"id": "h1"}}

    monkeypatch.setattr("api.main.run_incident", fake_run_incident)

    payload = {
        "title": "High error rate",
        "severity": "critical",
        "environment": "prod",
        "subject": "payments",
        "starts_at": "2024-01-01T12:00:00Z",
        "ends_at": "2024-01-01T12:05:00Z",
        "labels": {"k": "v"},
        "annotations": {"a": "b"},
    }

    resp = client.post("/webhook/incident", json=payload)
    assert resp.status_code == 200
    assert resp.json()["incident_summary"] == "incident ok"
