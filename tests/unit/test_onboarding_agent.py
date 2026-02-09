from __future__ import annotations

from core.onboarding_agent import apply_ops, plan_ops


def _base_model() -> dict:
    return {
        "providers": [
            {
                "id": "logs_primary",
                "category": "log_store",
                "type": "generic_log_api",
                "operations": ["query.samples"],
                "config": {},
            }
        ],
        "subjects": [
            {
                "name": "service_primary",
                "environment": "prod",
                "aliases": [],
                "bindings": {},
                "dependencies": [],
                "runbooks": [],
                "known_failure_modes": [],
                "deploy_context": {},
                "vcs_context": {},
                "log_evidence": {},
            }
        ],
    }


def test_plan_is_deterministic_for_same_intent():
    model = _base_model()
    intent = "add provider metrics_primary category metrics_store type generic_metrics_api operations query_range"

    first = plan_ops(intent, model)
    second = plan_ops(intent, model)

    assert first == second
    assert first["requires_confirmation"] is True
    assert len(first["proposed_ops"]) == 1


def test_mismatch_binding_is_rejected_when_policy_enforced():
    model = _base_model()
    ops = [
        {
            "type": "bind_subject_provider",
            "binding": {
                "subject": "service_primary",
                "capability": "vcs",
                "provider_id": "logs_primary",
            },
        }
    ]

    next_model, applied, rejected, warnings = apply_ops(model, ops, {"enforce_category_match": True})

    assert len(applied) == 0
    assert len(rejected) == 1
    assert any("does not match" in warning for warning in warnings)
    assert next_model["subjects"][0]["bindings"] == {}
