from __future__ import annotations

from pathlib import Path

import yaml
from fastapi.testclient import TestClient

import api.main as api


def _write_yaml(path: Path, doc: dict) -> None:
    path.write_text(yaml.safe_dump(doc, sort_keys=False))


def test_profile_switch_and_agent_endpoints_do_not_write_files(tmp_path, monkeypatch):
    template_catalog = tmp_path / "template.instances.yaml"
    template_kb = tmp_path / "template.subjects.yaml"
    demo_catalog = tmp_path / "demo.instances.yaml"
    demo_kb = tmp_path / "demo.subjects.yaml"
    target_catalog = tmp_path / "instances.yaml"
    target_kb = tmp_path / "subjects.yaml"

    _write_yaml(
        template_catalog,
        {
            "version": 1,
            "providers": [
                {
                    "id": "logs_primary",
                    "category": "log_store",
                    "type": "generic_log_api",
                    "capabilities": {"operations": ["query.samples"]},
                    "config": {},
                }
            ],
        },
    )
    _write_yaml(
        template_kb,
        {
            "version": 1,
            "subjects": [
                {
                    "name": "service_primary",
                    "environment": "prod",
                    "aliases": [],
                    "bindings": {"log_store": "logs_primary"},
                    "dependencies": [],
                    "runbooks": [],
                    "known_failure_modes": [],
                    "deploy_context": {},
                    "vcs_context": {},
                    "log_evidence": {
                        "parse": {"format": "json", "fields": {"env": "env", "err_msg": "message"}}
                    },
                }
            ],
        },
    )

    _write_yaml(
        demo_catalog,
        {
            "version": 1,
            "providers": [
                {
                    "id": "demo_logs",
                    "category": "log_store",
                    "type": "loki",
                    "capabilities": {"operations": ["query.samples"]},
                    "config": {},
                }
            ],
        },
    )
    _write_yaml(
        demo_kb,
        {
            "version": 1,
            "subjects": [
                {
                    "name": "demo_subject",
                    "environment": "prod",
                    "aliases": [],
                    "bindings": {"log_store": "demo_logs"},
                    "dependencies": [],
                    "runbooks": [],
                    "known_failure_modes": [],
                    "deploy_context": {},
                    "vcs_context": {},
                    "log_evidence": {
                        "parse": {"format": "json", "fields": {"env": "env", "err_msg": "message"}}
                    },
                }
            ],
        },
    )

    _write_yaml(target_catalog, {"version": 1, "providers": []})
    _write_yaml(target_kb, {"version": 1, "subjects": []})

    monkeypatch.setattr(api.settings, "onboarding_template_catalog_path", str(template_catalog))
    monkeypatch.setattr(api.settings, "onboarding_template_kb_path", str(template_kb))
    monkeypatch.setattr(api.settings, "onboarding_demo_catalog_path", str(demo_catalog))
    monkeypatch.setattr(api.settings, "onboarding_demo_kb_path", str(demo_kb))
    monkeypatch.setattr(api.settings, "catalog_path", str(target_catalog))
    monkeypatch.setattr(api.settings, "kb_path", str(target_kb))

    client = TestClient(api.app)

    template_resp = client.get("/knowledge/onboarding/model?profile=template")
    assert template_resp.status_code == 200
    template_model = template_resp.json()["model"]
    assert template_model["subjects"][0]["name"] == "service_primary"

    demo_resp = client.get("/knowledge/onboarding/model?profile=demo")
    assert demo_resp.status_code == 200
    demo_model = demo_resp.json()["model"]
    assert demo_model["subjects"][0]["name"] == "demo_subject"

    plan_resp = client.post(
        "/knowledge/onboarding/agent/plan",
        json={
            "intent": "add provider metrics_primary category metrics_store type generic_metrics_api operations query_range",
            "model": template_model,
            "policy": {"enforce_category_match": True},
        },
    )
    assert plan_resp.status_code == 200
    plan_data = plan_resp.json()
    assert len(plan_data["proposed_ops"]) == 1
    assert any(provider["id"] == "metrics_primary" for provider in plan_data["preview_model"]["providers"])

    before_catalog = target_catalog.read_text()
    before_kb = target_kb.read_text()

    apply_resp = client.post(
        "/knowledge/onboarding/agent/apply-ops",
        json={
            "model": template_model,
            "ops": plan_data["proposed_ops"],
            "policy": {"enforce_category_match": True},
        },
    )
    assert apply_resp.status_code == 200
    apply_data = apply_resp.json()
    assert any(provider["id"] == "metrics_primary" for provider in apply_data["model"]["providers"])

    mismatch_resp = client.post(
        "/knowledge/onboarding/agent/apply-ops",
        json={
            "model": apply_data["model"],
            "ops": [
                {
                    "type": "bind_subject_provider",
                    "binding": {
                        "subject": "service_primary",
                        "capability": "vcs",
                        "provider_id": "logs_primary",
                    },
                }
            ],
            "policy": {"enforce_category_match": True},
        },
    )
    assert mismatch_resp.status_code == 200
    mismatch_data = mismatch_resp.json()
    assert len(mismatch_data["rejected_ops"]) == 1
    assert any("does not match" in warning for warning in mismatch_data["warnings"])

    # Planner/apply-ops are model-only and must not write YAML files.
    assert target_catalog.read_text() == before_catalog
    assert target_kb.read_text() == before_kb


def test_model_preview_rejects_invalid_operation_against_rca_schema():
    client = TestClient(api.app)

    payload = {
        "model": {
            "providers": [
                {
                    "id": "bad_logs",
                    "category": "log_store",
                    "type": "custom",
                    "operations": ["totally_invalid_op"],
                    "config": {},
                }
            ],
            "subjects": [
                {
                    "name": "svc",
                    "environment": "prod",
                    "aliases": [],
                    "bindings": {"log_store": "bad_logs"},
                    "dependencies": [],
                    "runbooks": [],
                    "known_failure_modes": [],
                    "deploy_context": {},
                    "vcs_context": {},
                    "log_evidence": {
                        "parse": {"format": "json", "fields": {"env": "env", "err_msg": "message"}}
                    },
                }
            ],
        }
    }
    resp = client.post("/knowledge/onboarding/model/preview", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert any("totally_invalid_op" in err for err in body["errors"])


def test_model_preview_rejects_unknown_category_against_rca_schema():
    client = TestClient(api.app)

    payload = {
        "model": {
            "providers": [
                {
                    "id": "mystery_provider",
                    "category": "mystery_store",
                    "type": "custom",
                    "operations": ["query.samples"],
                    "config": {},
                }
            ],
            "subjects": [
                {
                    "name": "svc",
                    "environment": "prod",
                    "aliases": [],
                    "bindings": {"mystery_store": "mystery_provider"},
                    "dependencies": [],
                    "runbooks": [],
                    "known_failure_modes": [],
                    "deploy_context": {},
                    "vcs_context": {},
                    "log_evidence": {
                        "parse": {"format": "json", "fields": {"env": "env", "err_msg": "message"}}
                    },
                }
            ],
        }
    }
    resp = client.post("/knowledge/onboarding/model/preview", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert any("mystery_store" in err for err in body["errors"])
