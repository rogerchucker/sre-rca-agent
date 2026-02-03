from __future__ import annotations
from typing import Any, Dict

# Import concrete providers here (not in core)
from providers.log_store.loki import LokiLogStore
from providers.vcs.github import GitHubVCS
from providers.deploy_tracker.github_actions import GitHubActionsDeployTracker

def _factory(cls):
    def create(provider_id: str, config: Dict[str, Any]):
        return cls(provider_id=provider_id, config=config)
    return create

# key format: "{category}:{type}"
FACTORIES = {
    "log_store:loki": _factory(LokiLogStore),
    "vcs:github": _factory(GitHubVCS),
    "deploy_tracker:github_actions": _factory(GitHubActionsDeployTracker),
}