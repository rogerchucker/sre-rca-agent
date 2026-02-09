from __future__ import annotations

from core import orchestrator
from core.models import EvidenceItem, TimeRange, IncidentInput, Hypothesis, LogQueryRequest, DeployQueryRequest, BuildQueryRequest, ChangeQueryRequest, MetricsQueryRequest, TraceQueryRequest, AlertQueryRequest, EventQueryRequest, K8sLogQueryRequest


class DummyRegistry:
    def __init__(self, providers):
        self.providers = providers

    def get(self, provider_id: str):
        return self.providers[provider_id]


class DummyLogProvider:
    def query(self, req: LogQueryRequest) -> EvidenceItem:
        return EvidenceItem(
            id="log1",
            kind="log",
            source="log_store",
            time_range=req.time_range,
            query="q",
            summary="s",
            samples=[],
            top_signals={"signatures": []},
            pointers=[],
            tags=[],
        )


class DummyDeployProvider:
    def list_deployments(self, req: DeployQueryRequest) -> EvidenceItem:
        return EvidenceItem(
            id="deploy1",
            kind="deployment",
            source="deploy",
            time_range=req.time_range,
            query="q",
            summary="s",
            samples=[],
            top_signals={"deployment_refs": ["run:1"]},
            pointers=[],
            tags=[],
        )

    def get_deployment_metadata(self, deployment_ref: str) -> EvidenceItem:
        return EvidenceItem(
            id="deploy_meta",
            kind="deployment",
            source="deploy",
            time_range=TimeRange(start="", end=""),
            query="q",
            summary="meta",
            samples=[],
            top_signals={},
            pointers=[],
            tags=["metadata"],
        )


class DummyBuildProvider:
    def list_builds(self, req: BuildQueryRequest) -> EvidenceItem:
        return EvidenceItem(
            id="build1",
            kind="build",
            source="build",
            time_range=req.time_range,
            query="q",
            summary="s",
            samples=[],
            top_signals={"build_refs": ["run:1"]},
            pointers=[],
            tags=[],
        )

    def get_build_metadata(self, build_ref: str) -> EvidenceItem:
        return EvidenceItem(
            id="build_meta",
            kind="build",
            source="build",
            time_range=TimeRange(start="", end=""),
            query="q",
            summary="meta",
            samples=[],
            top_signals={},
            pointers=[],
            tags=["metadata"],
        )


class DummyVCSProvider:
    def list_changes(self, req: ChangeQueryRequest) -> EvidenceItem:
        return EvidenceItem(
            id="change1",
            kind="change",
            source="vcs",
            time_range=req.time_range,
            query="q",
            summary="s",
            samples=[],
            top_signals={},
            pointers=[],
            tags=[],
        )


class DummyMetricsProvider:
    def query_range(self, req: MetricsQueryRequest) -> EvidenceItem:
        return EvidenceItem(
            id="metric1",
            kind="metric",
            source="metrics",
            time_range=req.time_range,
            query=req.query,
            summary="s",
            samples=[],
            top_signals={},
            pointers=[],
            tags=[],
        )


class DummyTraceProvider:
    def search_traces(self, req: TraceQueryRequest) -> EvidenceItem:
        return EvidenceItem(
            id="trace1",
            kind="trace",
            source="trace",
            time_range=req.time_range,
            query="q",
            summary="s",
            samples=[],
            top_signals={},
            pointers=[],
            tags=[],
        )


class DummyAlertingProvider:
    def list_alerts(self, req: AlertQueryRequest) -> EvidenceItem:
        return EvidenceItem(
            id="alert1",
            kind="alert",
            source="alerting",
            time_range=req.time_range,
            query="q",
            summary="s",
            samples=[],
            top_signals={},
            pointers=[],
            tags=[],
        )


class DummyRuntimeProvider:
    def get_logs(self, req: K8sLogQueryRequest) -> EvidenceItem:
        return EvidenceItem(
            id="klog1",
            kind="log",
            source="runtime",
            time_range=req.time_range,
            query="q",
            summary="s",
            samples=[],
            top_signals={},
            pointers=[],
            tags=[],
        )

    def get_events(self, req: EventQueryRequest) -> EvidenceItem:
        return EvidenceItem(
            id="event1",
            kind="event",
            source="runtime",
            time_range=req.time_range,
            query="q",
            summary="s",
            samples=[],
            top_signals={"reasons": {}},
            pointers=[],
            tags=[],
        )


def _incident() -> IncidentInput:
    tr = TimeRange(start="2024-01-01T00:00:00Z", end="2024-01-01T00:10:00Z")
    return IncidentInput(
        title="t",
        severity="p1",
        environment="prod",
        subject="svc",
        time_range=tr,
        labels={},
        annotations={},
        raw={},
    )


def test_normalize_incident_environment(monkeypatch):
    state = {
        "raw_webhook": {
            "labels": {
                "environment": "production",
                "severity": "critical",
                "subject": "svc",
            },
            "annotations": {"summary": "s"},
        }
    }
    out = orchestrator.normalize_incident(state)
    assert out["incident"]["environment"] == "prod"


def test_safe_json():
    assert orchestrator._safe_json("not-json") == {}


def test_evidence_id():
    eid = orchestrator._evidence_id("x", "y")
    assert eid.startswith("x_")


def test_available_tools_and_missing():
    subject_cfg = {"bindings": {"log_store": "l", "runtime": "r", "deploy_tracker": "d", "vcs": "v", "build_tracker": "b", "metrics_store": "m", "trace_store": "t"}}
    tools = orchestrator._available_tools(subject_cfg)
    assert "query_logs" in tools
    missing = orchestrator._missing_evidence_kinds(tools, [])
    assert "log" in missing


def test_fallback_plan():
    plan = orchestrator._fallback_plan(["query_logs"], ["log"])
    assert plan


def test_add_kb_evidence_items():
    tr = TimeRange(start="2024-01-01T00:00:00Z", end="2024-01-01T00:10:00Z")
    subject_cfg = {
        "dependencies": [{"name": "db"}],
        "runbooks": [{"title": "rb"}],
    }
    evidence = orchestrator._add_kb_evidence_items([], subject_cfg, tr)
    kinds = {e.kind for e in evidence}
    assert "service_graph" in kinds
    assert "runbook" in kinds


def test_derive_helpers():
    tr = TimeRange(start="2024-01-01T00:00:00Z", end="2024-01-01T00:10:00Z")
    evidence = [
        EvidenceItem(
            id="e1",
            kind="deployment",
            source="x",
            time_range=tr,
            query="q",
            summary="s",
            samples=[],
            top_signals={"id": 1},
            pointers=[],
            tags=[],
        ),
        EvidenceItem(
            id="e2",
            kind="log",
            source="x",
            time_range=tr,
            query="q",
            summary="s",
            samples=[],
            top_signals={"signatures": ["boom"]},
            pointers=[],
            tags=[],
        ),
        EvidenceItem(
            id="e3",
            kind="event",
            source="x",
            time_range=tr,
            query="q",
            summary="s",
            samples=[],
            top_signals={"reasons": {"Crash": 1}},
            pointers=[],
            tags=[],
        ),
    ]
    assert orchestrator._derive_what_changed(evidence)["deployments"]
    assert orchestrator._derive_impact_scope(evidence)["error_signatures"]


def test_format_supporting_evidence():
    tr = TimeRange(start="2024-01-01T00:00:00Z", end="2024-01-01T00:10:00Z")
    ev = EvidenceItem(
        id="e1",
        kind="log",
        source="x",
        time_range=tr,
        query="q",
        summary="s",
        samples=[],
        top_signals={},
        pointers=[{"title": "link", "url": "u"}],
        tags=[],
    )
    h = Hypothesis(
        id="h1",
        statement="s",
        confidence=0.0,
        score_breakdown={},
        supporting_evidence_ids=["e1"],
        contradictions=[],
        validations=[],
    )
    out = orchestrator._format_supporting_evidence(h, [ev])
    assert out


def test_maybe_fetch_metadata():
    incident = _incident()
    subject_cfg = {"bindings": {"deploy_tracker": "d", "build_tracker": "b"}}

    registry = DummyRegistry({"d": DummyDeployProvider(), "b": DummyBuildProvider()})
    evidence = [DummyDeployProvider().list_deployments(DeployQueryRequest(subject="svc", environment="prod", time_range=incident.time_range))]
    evidence = orchestrator._maybe_fetch_deploy_metadata(evidence, subject_cfg, registry)
    assert any(e.tags and "metadata" in e.tags for e in evidence)

    evidence = [DummyBuildProvider().list_builds(BuildQueryRequest(subject="svc", environment="prod", time_range=incident.time_range))]
    evidence = orchestrator._maybe_fetch_build_metadata(evidence, subject_cfg, registry)
    assert any(e.tags and "metadata" in e.tags for e in evidence)


def test_execute_tool_calls():
    incident = _incident()
    subject_cfg = {
        "bindings": {
            "log_store": "l",
            "runtime": "r",
            "deploy_tracker": "d",
            "vcs": "v",
            "build_tracker": "b",
            "metrics_store": "m",
            "trace_store": "t",
            "alerting": "a",
        },
        "log_evidence": {"stream_selectors": {}, "parse": {}, "default_filters": {}},
    }
    registry = DummyRegistry({
        "l": DummyLogProvider(),
        "r": DummyRuntimeProvider(),
        "d": DummyDeployProvider(),
        "v": DummyVCSProvider(),
        "b": DummyBuildProvider(),
        "m": DummyMetricsProvider(),
        "t": DummyTraceProvider(),
        "a": DummyAlertingProvider(),
    })

    assert orchestrator._execute_tool_call("query_logs", {}, incident, subject_cfg, registry)
    assert orchestrator._execute_tool_call("list_alerts", {}, incident, subject_cfg, registry)
    assert orchestrator._execute_tool_call("query_k8s_logs", {}, incident, subject_cfg, registry)
    assert orchestrator._execute_tool_call("list_k8s_events", {}, incident, subject_cfg, registry)
    assert orchestrator._execute_tool_call("list_deployments", {}, incident, subject_cfg, registry)
    assert orchestrator._execute_tool_call("get_deployment_metadata", {"deployment_ref": "run:1"}, incident, subject_cfg, registry)
    assert orchestrator._execute_tool_call("list_changes", {}, incident, subject_cfg, registry)
    assert orchestrator._execute_tool_call("list_builds", {}, incident, subject_cfg, registry)
    assert orchestrator._execute_tool_call("get_build_metadata", {"build_ref": "run:1"}, incident, subject_cfg, registry)
    assert orchestrator._execute_tool_call("query_metrics", {"query": "up"}, incident, subject_cfg, registry)
    assert orchestrator._execute_tool_call("query_traces", {}, incident, subject_cfg, registry)
    assert orchestrator._execute_tool_call("unknown", {}, incident, subject_cfg, registry) is None
