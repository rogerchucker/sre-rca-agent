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
