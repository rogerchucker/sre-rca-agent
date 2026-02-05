from __future__ import annotations

from datetime import datetime, timezone
import json
import os

import pytest

from core.models import (
    LogQueryRequest,
    MetricsQueryRequest,
    TraceQueryRequest,
    DeployQueryRequest,
    ChangeQueryRequest,
    BuildQueryRequest,
    TimeRange,
)
from providers.log_store.loki import LokiLogStore
from providers.metrics_store.prometheus import PrometheusMetricsStore
from providers.trace_store.jaeger import JaegerTraceStore
from providers.deploy_tracker.github_actions import GitHubActionsDeployTracker
from providers.vcs.github import GitHubVCS
from providers.build_tracker.github_actions_builds import GitHubActionsBuildTracker


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class DummyClient:
    def __init__(self, payload):
        self.payload = payload
        self.last = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get(self, url, params=None):
        self.last = (url, params)
        return DummyResponse(self.payload)


class DummyPostClient(DummyClient):
    def post(self, url, json=None, timeout=None):
        self.last = (url, json)
        return DummyResponse(self.payload)


def test_loki_query_samples(monkeypatch):
    tr = TimeRange(start="2024-01-01T00:00:00Z", end="2024-01-01T00:10:00Z")
    req = LogQueryRequest(
        subject="svc",
        environment="prod",
        time_range=tr,
        intent="samples",
        stream_selectors={"app": "svc"},
        parse={"format": "json", "fields": {"err_msg": "attributes.error"}},
        filters={},
        limit=2,
    )

    payload = {
        "data": {
            "result": [
                {"values": [["1", "line1"], ["2", "line2"]]}
            ]
        }
    }
    monkeypatch.setattr("httpx.Client", lambda *args, **kwargs: DummyClient(payload))
    store = LokiLogStore("loki", {"base_url_env": "LOG_STORE_URL", "auth": {"kind": "none"}})
    ev = store.query(req)
    assert ev.kind == "log"
    assert len(ev.samples) == 2


def test_loki_query_signatures(monkeypatch):
    tr = TimeRange(start="2024-01-01T00:00:00Z", end="2024-01-01T00:10:00Z")
    req = LogQueryRequest(
        subject="svc",
        environment="prod",
        time_range=tr,
        intent="signature_counts",
        stream_selectors={"app": "svc"},
        parse={"format": "json", "fields": {"err_msg": "attributes.error.message"}},
        filters={},
        limit=2,
    )
    payload = {
        "data": {
            "result": [
                {"metric": {"err_msg": "boom"}, "values": [["1", "3"]]}
            ]
        }
    }
    monkeypatch.setattr("httpx.Client", lambda *args, **kwargs: DummyClient(payload))
    store = LokiLogStore("loki", {"base_url_env": "LOG_STORE_URL", "auth": {"kind": "none"}})
    ev = store.query(req)
    assert ev.kind == "log"
    assert ev.top_signals["signatures"]


def test_prometheus_query_range(monkeypatch):
    tr = TimeRange(start="2024-01-01T00:00:00Z", end="2024-01-01T00:10:00Z")
    req = MetricsQueryRequest(subject="svc", environment="prod", time_range=tr, query="up")
    payload = {
        "data": {
            "result": [
                {"metric": {"job": "svc"}, "values": [["1", "1"]]}
            ]
        }
    }
    monkeypatch.setattr("httpx.Client", lambda *args, **kwargs: DummyClient(payload))
    store = PrometheusMetricsStore("m", {"base_url_env": "METRICS_URL", "auth": {"kind": "none"}})
    ev = store.query_range(req)
    assert ev.kind == "metric"


def test_jaeger_search_traces(monkeypatch):
    tr = TimeRange(start="2024-01-01T00:00:00Z", end="2024-01-01T00:10:00Z")
    req = TraceQueryRequest(subject="svc", environment="prod", time_range=tr)
    payload = {"data": [{"traceID": "t1"}]}
    monkeypatch.setattr("httpx.Client", lambda *args, **kwargs: DummyClient(payload))
    store = JaegerTraceStore("t", {"base_url_env": "TRACE_URL", "auth": {"kind": "none"}})
    ev = store.search_traces(req)
    assert ev.samples == ["t1"]


def test_github_vcs_list_changes(monkeypatch):
    tr = TimeRange(start="2024-01-01T00:00:00Z", end="2024-01-01T00:10:00Z")
    req = ChangeQueryRequest(subject="svc", environment="prod", time_range=tr)
    payload = [
        {
            "number": 1,
            "title": "Fix",
            "merged_at": "2024-01-01T00:05:00Z",
            "user": {"login": "dev"},
            "html_url": "https://example.invalid/pr/1",
        }
    ]
    monkeypatch.setattr("httpx.Client", lambda *args, **kwargs: DummyClient(payload))
    vcs = GitHubVCS("v", {"token_env": "VCS_TOKEN", "repo_map": {"svc": "org/repo"}})
    ev = vcs.list_changes(req)
    assert ev.kind == "change"


def test_github_actions_deploy_tracker(monkeypatch):
    tr = TimeRange(start="2024-01-01T00:00:00Z", end="2024-01-01T00:10:00Z")
    req = DeployQueryRequest(subject="svc", environment="prod", time_range=tr)
    payload = {"workflow_runs": [{"id": 1, "created_at": "2024-01-01T00:05:00Z", "head_branch": "demo"}]}
    monkeypatch.setattr("httpx.Client", lambda *args, **kwargs: DummyClient(payload))

    tracker = GitHubActionsDeployTracker(
        "d",
        {
            "token_env": "DEPLOY_TOKEN",
            "repo_map": {"svc": "org/repo"},
            "workflow_path_map": {"svc": [".github/workflows/deploy.yml"]},
            "branch_allowlist": ["demo"],
            "markers": {"environment": "ENV=", "service": "SVC=", "sha": "SHA="},
        },
    )
    ev = tracker.list_deployments(req)
    assert ev.kind == "deployment"

    log_payload = {"url": "https://example.invalid/logs"}
    monkeypatch.setattr("httpx.Client", lambda *args, **kwargs: DummyClient(log_payload))
    monkeypatch.setattr(tracker, "_extract_markers_from_run_logs", lambda *a, **k: {"sha": "abc"})
    meta = tracker.get_deployment_metadata("run:1")
    assert meta.kind == "deployment"


def test_github_actions_build_tracker(monkeypatch):
    tr = TimeRange(start="2024-01-01T00:00:00Z", end="2024-01-01T00:10:00Z")
    req = BuildQueryRequest(subject="svc", environment="prod", time_range=tr)
    payload = {"workflow_runs": [{"id": 2, "created_at": "2024-01-01T00:05:00Z"}]}
    monkeypatch.setattr("httpx.Client", lambda *args, **kwargs: DummyClient(payload))

    tracker = GitHubActionsBuildTracker(
        "b",
        {
            "token_env": "BUILD_TOKEN",
            "repo_map": {"svc": "org/repo"},
            "workflow_path_map": {"svc": ".github/workflows/build.yml"},
            "markers": {"environment": "ENV=", "service": "SVC=", "sha": "SHA="},
        },
    )
    ev = tracker.list_builds(req)
    assert ev.kind == "build"

    monkeypatch.setattr(tracker, "_extract_markers_from_run_logs", lambda *a, **k: {"sha": "abc"})
    meta = tracker.get_build_metadata("run:2")
    assert meta.kind == "build"


def test_kubectl_runtime_logs_and_events(monkeypatch):
    from providers.runtime.kubectl import KubectlRuntime
    from core.models import K8sLogQueryRequest, EventQueryRequest

    tr = TimeRange(start="2024-01-01T00:00:00Z", end="2024-01-01T00:10:00Z")
    runtime = KubectlRuntime(
        "k",
        {
            "namespace_map": {"svc": "default"},
            "selector_map": {"svc": "app=svc"},
        },
    )

    def _fake_check_output(cmd, env=None, stderr=None):
        if "get" in cmd and "events" in cmd:
            return json.dumps({"items": [
                {"eventTime": "2024-01-01T00:05:00Z", "reason": "Crash", "type": "Warning", "message": "Boom"}
            ]}).encode("utf-8")
        return b"line1\nline2\n"

    monkeypatch.setattr("subprocess.check_output", _fake_check_output)

    log_req = K8sLogQueryRequest(subject="svc", environment="prod", time_range=tr)
    log_ev = runtime.get_logs(log_req)
    assert log_ev.kind == "log"

    ev_req = EventQueryRequest(subject="svc", environment="prod", time_range=tr)
    ev = runtime.get_events(ev_req)
    assert ev.kind == "event"


def test_kubectl_runtime_missing_namespace(monkeypatch):
    from providers.runtime.kubectl import KubectlRuntime
    from core.models import K8sLogQueryRequest

    tr = TimeRange(start="2024-01-01T00:00:00Z", end="2024-01-01T00:10:00Z")
    runtime = KubectlRuntime("k", {"selector_map": {"svc": "app=svc"}})
    req = K8sLogQueryRequest(subject="svc", environment="prod", time_range=tr)
    ev = runtime.get_logs(req)
    assert "missing namespace" in ev.summary


def test_env_required_raises(monkeypatch):
    monkeypatch.delenv("TRACE_URL", raising=False)
    from providers.trace_store.jaeger import _env_required as trace_env_required
    with pytest.raises(ValueError):
        trace_env_required(None)
    with pytest.raises(ValueError):
        trace_env_required("TRACE_URL")

def test_grafana_alerting_list_alerts(monkeypatch):
    from core.models import AlertQueryRequest
    from providers.alerting.grafana import GrafanaAlerting

    tr = TimeRange(start="2024-01-01T00:00:00Z", end="2024-01-01T00:10:00Z")
    req = AlertQueryRequest(subject="svc", environment="prod", time_range=tr, label_filters=["severity=critical"])

    payload = [
        {"labels": {"alertname": "HighError", "severity": "critical"}, "status": {"state": "firing"}},
    ]
    monkeypatch.setattr("httpx.Client", lambda *args, **kwargs: DummyClient(payload))
    alerting = GrafanaAlerting(
        "a",
        {
            "base_url_env": "GRAFANA_URL",
            "auth": {"kind": "basic_env", "username_env": "GRAFANA_USER", "token_env": "GRAFANA_TOKEN"},
        },
    )
    ev = alerting.list_alerts(req)
    assert ev.kind == "alert"
