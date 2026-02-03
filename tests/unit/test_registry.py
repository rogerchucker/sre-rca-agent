import pytest

from core.registry import ProviderRegistry


def test_registry_gets_instance():
    called = {}

    def factory(provider_id: str, config: dict):
        called["id"] = provider_id
        called["config"] = config
        return {"provider_id": provider_id}

    instances = {
        "p1": {"id": "p1", "category": "log_store", "type": "loki", "config": {"x": 1}},
    }
    reg = ProviderRegistry(factories={"log_store:loki": factory}, instances_config=instances)
    inst = reg.get("p1")
    assert inst["provider_id"] == "p1"
    assert called["config"] == {"x": 1}


def test_registry_missing_provider():
    reg = ProviderRegistry(factories={}, instances_config={})
    with pytest.raises(KeyError):
        reg.get("missing")


def test_registry_missing_category_type():
    reg = ProviderRegistry(factories={}, instances_config={"p1": {"id": "p1"}})
    with pytest.raises(ValueError):
        reg.get("p1")


def test_registry_missing_factory():
    reg = ProviderRegistry(
        factories={},
        instances_config={"p1": {"id": "p1", "category": "log_store", "type": "loki"}},
    )
    with pytest.raises(KeyError):
        reg.get("p1")
