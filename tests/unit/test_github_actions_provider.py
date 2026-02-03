from __future__ import annotations

import io
import zipfile
from datetime import datetime, timezone

import pytest

from providers.deploy_tracker.github_actions import GitHubActionsDeployTracker
from providers.build_tracker.github_actions_builds import GitHubActionsBuildTracker
from core.models import DeployQueryRequest, BuildQueryRequest, TimeRange


class DummyResponse:
    def __init__(self, json_data=None, content=b""):
        self._json = json_data
        self.content = content

    def json(self):
        return self._json

    def raise_for_status(self):
        return None


class DummyClient:
    def __init__(self, responses):
        self._responses = responses

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url, params=None):
        for prefix, resp in self._responses.items():
            if url.startswith(prefix):
                return resp
        raise AssertionError(f"Unexpected URL: {url}")


def test_list_runs_filters_time_window(monkeypatch):
    now = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    in_range = now.isoformat().replace("+00:00", "Z")
    out_range = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")

    data = {
        "workflow_runs": [
            {"id": 1, "created_at": in_range, "status": "completed", "conclusion": "success", "html_url": "u1", "head_sha": "s1"},
            {"id": 2, "created_at": out_range, "status": "completed", "conclusion": "success", "html_url": "u2", "head_sha": "s2"},
        ]
    }

    responses = {"https://api.github.com/": DummyResponse(json_data=data)}
    monkeypatch.setattr("providers.deploy_tracker.github_actions.httpx.Client", lambda **kwargs: DummyClient(responses))

    provider = GitHubActionsDeployTracker(
        "deploy_main",
        {
            "token_env": "DEPLOY_TOKEN",
            "repo_map": {"payments": "example-org/payments"},
            "workflow_path_map": {"payments": ".github/workflows/deploy.yml"},
            "markers": {},
        },
    )

    tr = TimeRange(start="2024-01-01T11:00:00Z", end="2024-01-01T13:00:00Z")
    req = DeployQueryRequest(subject="payments", environment="prod", time_range=tr, limit=20)
    ev = provider.list_deployments(req)
    assert ev.top_signals["deployment_refs"] == ["run:1"]


def test_extract_markers_from_run_logs(monkeypatch):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("log.txt", "ENV=prod\nSERVICE=payments\nSHA=abc123\n")
    zip_bytes = buf.getvalue()

    responses = {"https://api.github.com/": DummyResponse(content=zip_bytes)}
    monkeypatch.setattr("providers.deploy_tracker.github_actions.httpx.Client", lambda **kwargs: DummyClient(responses))

    provider = GitHubActionsDeployTracker(
        "deploy_main",
        {
            "token_env": "DEPLOY_TOKEN",
            "repo_map": {"payments": "example-org/payments"},
            "workflow_path_map": {"payments": ".github/workflows/deploy.yml"},
            "markers": {"environment": "ENV=", "service": "SERVICE=", "sha": "SHA="},
        },
    )

    ev = provider.get_deployment_metadata("run:42")
    meta = ev.top_signals["metadata"]
    assert meta["environment"] == "prod"
    assert meta["service"] == "payments"
    assert meta["sha"] == "abc123"


def test_build_list_runs_filters_time_window(monkeypatch):
    now = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    in_range = now.isoformat().replace("+00:00", "Z")
    out_range = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")

    data = {
        "workflow_runs": [
            {"id": 11, "created_at": in_range, "status": "completed", "conclusion": "success", "html_url": "u1", "head_sha": "s1"},
            {"id": 12, "created_at": out_range, "status": "completed", "conclusion": "success", "html_url": "u2", "head_sha": "s2"},
        ]
    }

    responses = {"https://api.github.com/": DummyResponse(json_data=data)}
    monkeypatch.setattr("providers.build_tracker.github_actions_builds.httpx.Client", lambda **kwargs: DummyClient(responses))

    provider = GitHubActionsBuildTracker(
        "build_main",
        {
            "token_env": "BUILD_TOKEN",
            "repo_map": {"payments": "example-org/payments"},
            "workflow_path_map": {"payments": ".github/workflows/build.yml"},
            "markers": {},
        },
    )

    tr = TimeRange(start="2024-01-01T11:00:00Z", end="2024-01-01T13:00:00Z")
    req = BuildQueryRequest(subject="payments", environment="prod", time_range=tr, limit=20)
    ev = provider.list_builds(req)
    assert ev.top_signals["build_refs"] == ["run:11"]


def test_build_extract_markers_from_run_logs(monkeypatch):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("log.txt", "BUILD_ENV=prod\nBUILD_SERVICE=payments\nBUILD_SHA=abc123\n")
    zip_bytes = buf.getvalue()

    responses = {"https://api.github.com/": DummyResponse(content=zip_bytes)}
    monkeypatch.setattr("providers.build_tracker.github_actions_builds.httpx.Client", lambda **kwargs: DummyClient(responses))

    provider = GitHubActionsBuildTracker(
        "build_main",
        {
            "token_env": "BUILD_TOKEN",
            "repo_map": {"payments": "example-org/payments"},
            "workflow_path_map": {"payments": ".github/workflows/build.yml"},
            "markers": {"environment": "BUILD_ENV=", "service": "BUILD_SERVICE=", "sha": "BUILD_SHA="},
        },
    )

    ev = provider.get_build_metadata("run:99")
    meta = ev.top_signals["metadata"]
    assert meta["environment"] == "prod"
    assert meta["service"] == "payments"
    assert meta["sha"] == "abc123"
