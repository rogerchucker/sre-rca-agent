from fastapi.testclient import TestClient

from api.main import app


def test_ui_summary_no_report():
    client = TestClient(app)
    resp = client.get("/ui/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "summary" in data
    assert "confidence" in data


def test_ui_mode():
    client = TestClient(app)
    resp = client.get("/ui/mode")
    assert resp.status_code == 200
    assert "live_mode" in resp.json()


def test_ui_attention_no_persistence():
    client = TestClient(app)
    resp = client.get("/ui/attention")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_signals_timeline_demo():
    client = TestClient(app)
    resp = client.get("/signals/timeline")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_signals_correlation_demo():
    client = TestClient(app)
    resp = client.get("/signals/correlation")
    assert resp.status_code == 200
    data = resp.json()
    assert "pairs" in data


def test_knowledge_runbooks_patterns():
    client = TestClient(app)
    runbooks = client.get("/knowledge/runbooks")
    patterns = client.get("/knowledge/patterns")
    assert runbooks.status_code == 200
    assert patterns.status_code == 200
    assert isinstance(runbooks.json(), list)
    assert isinstance(patterns.json(), list)
