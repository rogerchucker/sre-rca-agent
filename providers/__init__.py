from __future__ import annotations
from typing import Any, Dict

# Import concrete providers here (not in core)
from providers.log_store.loki import LokiLogStore
from providers.vcs.github import GitHubVCS
from providers.deploy_tracker.github_actions import GitHubActionsDeployTracker
from providers.runtime.kubectl import KubectlRuntime
from providers.metrics_store.prometheus import PrometheusMetricsStore
from providers.trace_store.jaeger import JaegerTraceStore
from providers.build_tracker.github_actions_builds import GitHubActionsBuildTracker

def _factory(cls):
    def create(provider_id: str, config: Dict[str, Any]):
        return cls(provider_id=provider_id, config=config)
    return create

# key format: "{category}:{type}"
FACTORIES = {
    "log_store:loki": _factory(LokiLogStore),
    "vcs:github": _factory(GitHubVCS),
    "deploy_tracker:github_actions": _factory(GitHubActionsDeployTracker),
    "runtime:kubectl": _factory(KubectlRuntime),
    "metrics_store:prometheus": _factory(PrometheusMetricsStore),
    "trace_store:jaeger": _factory(JaegerTraceStore),
    "build_tracker:github_actions": _factory(GitHubActionsBuildTracker),
}
