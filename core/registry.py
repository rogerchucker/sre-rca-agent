from __future__ import annotations
from typing import Any, Dict, Protocol

from core.models import (
    EvidenceItem,
    LogQueryRequest,
    DeployQueryRequest,
    ChangeQueryRequest,
    BuildQueryRequest,
    MetricsQueryRequest,
    TraceQueryRequest,
    EventQueryRequest,
    K8sLogQueryRequest,
)

# ---- Provider protocols (core-neutral) ----

class LogStoreProvider(Protocol):
    def query(self, req: LogQueryRequest) -> EvidenceItem: ...

class DeployTrackerProvider(Protocol):
    def list_deployments(self, req: DeployQueryRequest) -> EvidenceItem: ...
    def get_deployment_metadata(self, deployment_ref: str) -> EvidenceItem: ...

class VCSProvider(Protocol):
    def list_changes(self, req: ChangeQueryRequest) -> EvidenceItem: ...

class BuildTrackerProvider(Protocol):
    def list_builds(self, req: BuildQueryRequest) -> EvidenceItem: ...
    def get_build_metadata(self, build_ref: str) -> EvidenceItem: ...

class MetricsStoreProvider(Protocol):
    def query_range(self, req: MetricsQueryRequest) -> EvidenceItem: ...

class TraceStoreProvider(Protocol):
    def search_traces(self, req: TraceQueryRequest) -> EvidenceItem: ...

class RuntimeProvider(Protocol):
    def get_logs(self, req: K8sLogQueryRequest) -> EvidenceItem: ...
    def get_events(self, req: EventQueryRequest) -> EvidenceItem: ...

# ---- Registry ----

class ProviderRegistry:
    """
    Core does NOT import vendor SDKs. It loads concrete provider classes via a static mapping
    of (category, type) -> provider factory, which lives in providers/__init__.py.
    """
    def __init__(self, factories: Dict[str, Any], instances_config: Dict[str, Any]):
        self._factories = factories  # key like "log_store:loki"
        self._instances_config = instances_config
        self._instances: Dict[str, Any] = {}

    def get(self, provider_id: str):
        if provider_id in self._instances:
            return self._instances[provider_id]

        cfg = self._instances_config.get(provider_id)
        if not cfg:
            raise KeyError(f"Provider instance '{provider_id}' not found in KB providers")

        category = cfg.get("category")
        ptype = cfg.get("type")
        if not category or not ptype:
            raise ValueError(f"Provider '{provider_id}' must include category and type")

        key = f"{category}:{ptype}"
        factory = self._factories.get(key)
        if not factory:
            raise KeyError(f"No provider factory registered for '{key}'")

        instance = factory(provider_id=provider_id, config=cfg.get("config", {}))
        self._instances[provider_id] = instance
        return instance
