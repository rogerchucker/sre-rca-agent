from fastapi.testclient import TestClient

from api.main import app


def test_action_endpoints_require_persistence():
    client = TestClient(app)
    payload = {"incident_id": "inc-1", "name": "dry run"}
    resp = client.post("/actions/dry-run", json=payload)
    assert resp.status_code == 503
    resp = client.post("/actions/approve", json=payload)
    assert resp.status_code == 503
    resp = client.post("/actions/execute", json=payload)
    assert resp.status_code == 503


def test_audit_returns_empty_without_persistence():
    client = TestClient(app)
    resp = client.get("/audit")
    assert resp.status_code == 200
    assert resp.json() == []
