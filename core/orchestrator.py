from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from langgraph.graph import StateGraph, END

from openai import OpenAI
from core.config import settings
from core.models import (
    AgentState, IncidentInput, EvidenceItem, Hypothesis, RCAReport,
    LogQueryRequest, DeployQueryRequest, ChangeQueryRequest, TimeRange,
    BuildQueryRequest, MetricsQueryRequest, TraceQueryRequest,
    EventQueryRequest, K8sLogQueryRequest
)
from core.prompts import SYSTEM_PROMPT, HYPOTHESIS_TASK, PLAN_TASK, EVIDENCE_TOOL_SYSTEM
from core.scoring import rank

client = OpenAI(api_key=settings.openai_api_key)

CONFIDENCE_THRESHOLD = 0.62
MAX_ITERATIONS = 2

def _now_rfc3339() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def _shift_rfc3339(rfc3339: str, minutes: int) -> str:
    dt = datetime.fromisoformat(rfc3339.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (dt + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")

def build_graph():
    g = StateGraph(dict)

    g.add_node("normalize_incident", normalize_incident)
    g.add_node("load_kb_slice", load_kb_slice)
    g.add_node("seed_alert_evidence", seed_alert_evidence)

    g.add_node("plan_evidence", plan_evidence)
    g.add_node("collect_evidence_tools", collect_evidence_tools)

    g.add_node("hypothesize", hypothesize)
    g.add_node("score_and_report", score_and_report)

    g.set_entry_point("normalize_incident")
    g.add_edge("normalize_incident", "load_kb_slice")
    g.add_edge("load_kb_slice", "seed_alert_evidence")

    g.add_edge("seed_alert_evidence", "plan_evidence")
    g.add_edge("plan_evidence", "collect_evidence_tools")
    g.add_edge("collect_evidence_tools", "hypothesize")
    g.add_edge("hypothesize", "score_and_report")
    g.add_conditional_edges("score_and_report", decide_next, {"iterate": "plan_evidence", "end": END})

    return g.compile()

# ---- Nodes (core-neutral) ----

def normalize_incident(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accepts a webhook payload and maps it into a vendor-neutral IncidentInput.
    This parser is intentionally tolerant and does not assume a specific alerting product.
    """
    if state.get("incident"):
        return state
    raw = state.get("raw_webhook", {})
    alerts = raw.get("alerts") or []
    a0 = alerts[0] if alerts else raw

    labels = a0.get("labels") or raw.get("labels") or {}
    annotations = a0.get("annotations") or raw.get("annotations") or {}

    subject = labels.get("subject") or labels.get("service") or labels.get("job") or "unknown"
    environment = labels.get("environment") or labels.get("env") or "unknown"
    severity = labels.get("severity") or labels.get("level") or "unknown"

    title = annotations.get("summary") or annotations.get("description") or labels.get("alertname") or "incident"
    starts_at = a0.get("startsAt") or raw.get("startsAt")
    ends_at = a0.get("endsAt") or raw.get("endsAt") or _now_rfc3339()

    if not starts_at:
        ends_at = _now_rfc3339()
        starts_at = _shift_rfc3339(ends_at, -60)

    # Small buffer before start
    tr = TimeRange(start=_shift_rfc3339(starts_at, -10), end=ends_at)

    incident = IncidentInput(
        title=title,
        severity=severity,
        environment=environment,
        subject=subject,
        time_range=tr,
        labels=labels,
        annotations=annotations,
        raw=raw,
    )
    state["incident"] = incident.model_dump()
    return state

def load_kb_slice(state: Dict[str, Any]) -> Dict[str, Any]:
    from core.kb import KB
    from core.registry import ProviderRegistry
    from providers import FACTORIES  # mapping lives outside core logic

    incident = IncidentInput(**state["incident"])
    kb = KB.load(settings.kb_path)

    subject_cfg = kb.get_subject_config(incident.subject, incident.environment)
    provider_instances = kb.get_provider_instances()

    registry = ProviderRegistry(factories=FACTORIES, instances_config=provider_instances)

    # Persist only what core needs (no vendor specifics)
    state["kb_slice"] = {
        "subject_cfg": subject_cfg,
        "providers": provider_instances,
    }
    state["_registry"] = registry  # runtime object (not serializable, OK in-process)
    return state

def seed_alert_evidence(state: Dict[str, Any]) -> Dict[str, Any]:
    incident = IncidentInput(**state["incident"])
    e = EvidenceItem(
        id="alert_0",
        kind="alert",
        source="alert_webhook",
        time_range=incident.time_range,
        query="incoming_webhook",
        summary="Alert/incident webhook received; details captured in labels/annotations.",
        top_signals={"labels": incident.labels, "annotations": incident.annotations},
        samples=[],
        pointers=[],
        tags=["alert", "webhook"],
    )
    state["evidence"] = [e.model_dump()]
    return state

def plan_evidence(state: Dict[str, Any]) -> Dict[str, Any]:
    incident = IncidentInput(**state["incident"])
    subject_cfg = state["kb_slice"]["subject_cfg"]
    evidence = [EvidenceItem(**x) for x in state.get("evidence", [])]
    iteration = int(state.get("iteration", 0))

    available_tools = _available_tools(subject_cfg)
    missing = _missing_evidence_kinds(available_tools, evidence)

    payload = {
        "incident": incident.model_dump(),
        "knowledge": {
            "known_failure_modes": subject_cfg.get("known_failure_modes", []),
            "dependencies": subject_cfg.get("dependencies", []),
        },
        "evidence_summary": _compact_evidence(evidence),
        "available_tools": available_tools,
        "missing_evidence_kinds": missing,
        "task": PLAN_TASK,
        "iteration": iteration,
    }

    resp = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload)},
        ],
        temperature=0.2,
    )

    text = resp.choices[0].message.content or "{}"
    parsed = _safe_json(text)
    actions = parsed.get("actions") if isinstance(parsed, dict) else None
    if not isinstance(actions, list):
        actions = _fallback_plan(available_tools, missing)

    state["plan"] = actions
    return state

def collect_evidence_tools(state: Dict[str, Any]) -> Dict[str, Any]:
    incident = IncidentInput(**state["incident"])
    subject_cfg = state["kb_slice"]["subject_cfg"]
    registry = state["_registry"]
    evidence = [EvidenceItem(**x) for x in state.get("evidence", [])]
    plan = state.get("plan") or []

    tools = _tool_schemas(subject_cfg)
    tool_choice = "required" if plan else "auto"

    payload = {
        "incident": incident.model_dump(),
        "plan": plan,
        "note": "Follow the plan order when calling tools. Skip tools not available.",
    }

    resp = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": EVIDENCE_TOOL_SYSTEM},
            {"role": "user", "content": json.dumps(payload)},
        ],
        tools=tools,
        tool_choice=tool_choice,
        temperature=0.0,
    )

    msg = resp.choices[0].message
    tool_calls = getattr(msg, "tool_calls", None) or []

    if not tool_calls and plan:
        # Fallback: execute plan directly if the model returned no tool calls
        for action in plan:
            ev = _execute_planned_action(action, incident, subject_cfg, registry)
            if ev:
                evidence.append(ev)
        state["evidence"] = [e.model_dump() for e in evidence]
        return state

    for call in tool_calls:
        name = call.function.name
        args = _safe_json(call.function.arguments or "{}")
        ev = _execute_tool_call(name, args, incident, subject_cfg, registry)
        if ev:
            evidence.append(ev)

    evidence = _maybe_fetch_deploy_metadata(evidence, subject_cfg, registry)
    evidence = _maybe_fetch_build_metadata(evidence, subject_cfg, registry)
    state["evidence"] = [e.model_dump() for e in evidence]
    return state

def hypothesize(state: Dict[str, Any]) -> Dict[str, Any]:
    incident = IncidentInput(**state["incident"])
    evidence = [EvidenceItem(**x) for x in state.get("evidence", [])]
    subject_cfg = state["kb_slice"]["subject_cfg"]

    compact = _compact_evidence(evidence)

    payload = {
        "incident": incident.model_dump(),
        "knowledge": {
            "known_failure_modes": subject_cfg.get("known_failure_modes", []),
            "runbooks": subject_cfg.get("runbooks", []),
            "dependencies": subject_cfg.get("dependencies", []),
        },
        "evidence": compact,
        "task": HYPOTHESIS_TASK,
    }

    resp = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload)},
        ],
        temperature=0.2,
    )

    text = resp.choices[0].message.content or "{}"
    try:
        parsed = json.loads(text)
    except Exception:
        parsed = {"hypotheses": []}

    hyps: List[Hypothesis] = []
    for i, h in enumerate(parsed.get("hypotheses", [])[:5]):
        hyps.append(Hypothesis(
            id=h.get("id") or f"h{i+1}",
            statement=h.get("statement", ""),
            confidence=0.0,
            score_breakdown={},
            supporting_evidence_ids=h.get("supporting_evidence_ids", []),
            contradictions=h.get("contradictions", []),
            validations=h.get("validations", []),
        ))

    state["hypotheses"] = [h.model_dump() for h in hyps]
    return state

def score_and_report(state: Dict[str, Any]) -> Dict[str, Any]:
    incident = IncidentInput(**state["incident"])
    evidence = [EvidenceItem(**x) for x in state.get("evidence", [])]
    hyps = [Hypothesis(**x) for x in state.get("hypotheses", [])]

    ranked = rank(hyps, evidence)
    if ranked:
        top = ranked[0]
        others = ranked[1:]
        next_validations = top.validations[:5]
    else:
        top = Hypothesis(
            id="h0",
            statement="Insufficient evidence to form a confident hypothesis.",
            confidence=0.0,
            score_breakdown={"total": 0.0},
            supporting_evidence_ids=[],
            validations=["Collect additional logs and deploy/change context for the time window."],
            contradictions=[],
        )
        others = []
        next_validations = top.validations

    report = RCAReport(
        incident_summary=f"{incident.title} (severity={incident.severity}, env={incident.environment})",
        time_range=incident.time_range,
        top_hypothesis=top,
        other_hypotheses=others,
        evidence=evidence,
        next_validations=next_validations,
    )
    state["report"] = report.model_dump()
    iteration = int(state.get("iteration", 0))
    should_iterate = top.confidence < CONFIDENCE_THRESHOLD and iteration < MAX_ITERATIONS
    state["should_iterate"] = should_iterate
    if should_iterate:
        state["iteration"] = iteration + 1
    return state

def decide_next(state: Dict[str, Any]) -> str:
    return "iterate" if state.get("should_iterate") else "end"


def _compact_evidence(evidence: List[EvidenceItem]) -> List[Dict[str, Any]]:
    compact = []
    for e in evidence:
        compact.append({
            "id": e.id,
            "kind": e.kind,
            "summary": e.summary,
            "top_signals": e.top_signals,
            "sample_preview": e.samples[:8],
        })
    return compact

def _safe_json(text: str) -> Dict[str, Any]:
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}

def _available_tools(subject_cfg: Dict[str, Any]) -> List[str]:
    tools: List[str] = []
    bindings = subject_cfg.get("bindings", {})
    if bindings.get("log_store"):
        tools.append("query_logs")
    if bindings.get("runtime"):
        tools.append("query_k8s_logs")
        tools.append("list_k8s_events")
    if bindings.get("deploy_tracker"):
        tools.append("list_deployments")
        tools.append("get_deployment_metadata")
    if bindings.get("build_tracker"):
        tools.append("list_builds")
        tools.append("get_build_metadata")
    if bindings.get("vcs"):
        tools.append("list_changes")
    if bindings.get("metrics_store"):
        tools.append("query_metrics")
    if bindings.get("trace_store"):
        tools.append("query_traces")
    return tools

def _missing_evidence_kinds(available_tools: List[str], evidence: List[EvidenceItem]) -> List[str]:
    kinds = {e.kind for e in evidence}
    missing = []
    if "query_logs" in available_tools and "logs" not in kinds:
        missing.append("logs")
    if "query_k8s_logs" in available_tools and "logs" not in kinds:
        missing.append("logs")
    if "list_k8s_events" in available_tools and "event" not in kinds:
        missing.append("event")
    if "list_deployments" in available_tools and "deploy" not in kinds:
        missing.append("deploy")
    if "list_builds" in available_tools and "build" not in kinds:
        missing.append("build")
    if "list_changes" in available_tools and "change" not in kinds:
        missing.append("change")
    if "query_metrics" in available_tools and "metrics" not in kinds:
        missing.append("metrics")
    if "query_traces" in available_tools and "trace" not in kinds:
        missing.append("trace")
    return missing

def _fallback_plan(available_tools: List[str], missing: List[str]) -> List[Dict[str, Any]]:
    plan: List[Dict[str, Any]] = []
    if "query_logs" in available_tools:
        if "logs" in missing or not missing:
            plan.append({"tool": "query_logs", "args": {"intent": "signature_counts", "limit": 200}})
            plan.append({"tool": "query_logs", "args": {"intent": "samples", "limit": 80}})
    if "query_k8s_logs" in available_tools and ("logs" in missing or not missing):
        plan.append({"tool": "query_k8s_logs", "args": {"limit": 120}})
    if "list_k8s_events" in available_tools and ("event" in missing or not missing):
        plan.append({"tool": "list_k8s_events", "args": {"limit": 200}})
    if "list_deployments" in available_tools and "deploy" in missing:
        plan.append({"tool": "list_deployments", "args": {"window_minutes_before": 30, "window_minutes_after": 30, "limit": 20}})
    if "list_builds" in available_tools and "build" in missing:
        plan.append({"tool": "list_builds", "args": {"window_minutes_before": 60, "window_minutes_after": 60, "limit": 20}})
    if "list_changes" in available_tools and "change" in missing:
        plan.append({"tool": "list_changes", "args": {"window_minutes_before": 360, "include_prs": True, "include_commits": False, "limit": 30}})
    if "query_metrics" in available_tools and "metrics" in missing:
        plan.append({"tool": "query_metrics", "args": {"query": "up", "step_seconds": 60, "limit": 50}})
    if "query_traces" in available_tools and "trace" in missing:
        plan.append({"tool": "query_traces", "args": {"limit": 20}})
    return plan

def _tool_schemas(subject_cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    tools = []
    bindings = subject_cfg.get("bindings", {})

    if bindings.get("log_store"):
        tools.append({
            "type": "function",
            "function": {
                "name": "query_logs",
                "description": "Collect log evidence for the incident time window.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "intent": {"type": "string", "enum": ["signature_counts", "samples"]},
                        "filter_expressions": {"type": "array", "items": {"type": "string"}},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 500},
                    },
                    "required": ["intent"],
                },
            },
        })
    if bindings.get("runtime"):
        tools.append({
            "type": "function",
            "function": {
                "name": "query_k8s_logs",
                "description": "Collect kubernetes logs for the incident time window.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "namespace": {"type": "string"},
                        "selector": {"type": "string"},
                        "container": {"type": "string"},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 500},
                    },
                },
            },
        })
        tools.append({
            "type": "function",
            "function": {
                "name": "list_k8s_events",
                "description": "Collect kubernetes events for the incident time window.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "namespace": {"type": "string"},
                        "selector": {"type": "string"},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 500},
                    },
                },
            },
        })
    if bindings.get("deploy_tracker"):
        tools.append({
            "type": "function",
            "function": {
                "name": "list_deployments",
                "description": "List deployment runs around the incident window.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "window_minutes_before": {"type": "integer", "minimum": 5, "maximum": 1440},
                        "window_minutes_after": {"type": "integer", "minimum": 5, "maximum": 1440},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                    },
                },
            },
        })
        tools.append({
            "type": "function",
            "function": {
                "name": "get_deployment_metadata",
                "description": "Fetch deployment metadata for a deployment reference.",
                "parameters": {
                    "type": "object",
                    "properties": {"deployment_ref": {"type": "string"}},
                    "required": ["deployment_ref"],
                },
            },
        })
    if bindings.get("vcs"):
        tools.append({
            "type": "function",
            "function": {
                "name": "list_changes",
                "description": "List code changes near the incident window.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "window_minutes_before": {"type": "integer", "minimum": 30, "maximum": 10080},
                        "include_prs": {"type": "boolean"},
                        "include_commits": {"type": "boolean"},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                    },
                },
            },
        })
    if bindings.get("build_tracker"):
        tools.append({
            "type": "function",
            "function": {
                "name": "list_builds",
                "description": "List build runs around the incident window.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "window_minutes_before": {"type": "integer", "minimum": 5, "maximum": 1440},
                        "window_minutes_after": {"type": "integer", "minimum": 5, "maximum": 1440},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                    },
                },
            },
        })
        tools.append({
            "type": "function",
            "function": {
                "name": "get_build_metadata",
                "description": "Fetch build metadata for a build reference.",
                "parameters": {
                    "type": "object",
                    "properties": {"build_ref": {"type": "string"}},
                    "required": ["build_ref"],
                },
            },
        })
    if bindings.get("metrics_store"):
        tools.append({
            "type": "function",
            "function": {
                "name": "query_metrics",
                "description": "Query metrics in the incident time window.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "step_seconds": {"type": "integer", "minimum": 10, "maximum": 600},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 200},
                    },
                    "required": ["query"],
                },
            },
        })
    if bindings.get("trace_store"):
        tools.append({
            "type": "function",
            "function": {
                "name": "query_traces",
                "description": "Search traces for the incident time window.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "service_name": {"type": "string"},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                    },
                },
            },
        })
    return tools

def _execute_planned_action(action: Dict[str, Any], incident: IncidentInput, subject_cfg: Dict[str, Any], registry):
    tool = action.get("tool")
    args = action.get("args") or {}
    return _execute_tool_call(tool, args, incident, subject_cfg, registry)

def _execute_tool_call(tool: str, args: Dict[str, Any], incident: IncidentInput, subject_cfg: Dict[str, Any], registry):
    if tool == "query_logs":
        return _call_query_logs(args, incident, subject_cfg, registry)
    if tool == "query_k8s_logs":
        return _call_query_k8s_logs(args, incident, subject_cfg, registry)
    if tool == "list_k8s_events":
        return _call_list_k8s_events(args, incident, subject_cfg, registry)
    if tool == "list_deployments":
        return _call_list_deployments(args, incident, subject_cfg, registry)
    if tool == "get_deployment_metadata":
        return _call_get_deployment_metadata(args, subject_cfg, registry)
    if tool == "list_changes":
        return _call_list_changes(args, incident, subject_cfg, registry)
    if tool == "list_builds":
        return _call_list_builds(args, incident, subject_cfg, registry)
    if tool == "get_build_metadata":
        return _call_get_build_metadata(args, subject_cfg, registry)
    if tool == "query_metrics":
        return _call_query_metrics(args, incident, subject_cfg, registry)
    if tool == "query_traces":
        return _call_query_traces(args, incident, subject_cfg, registry)
    return None

def _maybe_fetch_deploy_metadata(evidence: List[EvidenceItem], subject_cfg: Dict[str, Any], registry) -> List[EvidenceItem]:
    deploy_id = subject_cfg.get("bindings", {}).get("deploy_tracker")
    if not deploy_id:
        return evidence
    if any(e.kind == "deploy" and "metadata" in (e.tags or []) for e in evidence):
        return evidence
    refs: List[str] = []
    for e in evidence:
        if e.kind != "deploy":
            continue
        refs = (e.top_signals or {}).get("deployment_refs") or []
        if refs:
            break
    if not refs:
        return evidence
    deploy_provider = registry.get(deploy_id)
    try:
        meta = deploy_provider.get_deployment_metadata(refs[0])
        evidence.append(meta)
    except Exception:
        pass
    return evidence

def _maybe_fetch_build_metadata(evidence: List[EvidenceItem], subject_cfg: Dict[str, Any], registry) -> List[EvidenceItem]:
    build_id = subject_cfg.get("bindings", {}).get("build_tracker")
    if not build_id:
        return evidence
    if any(e.kind == "build" and "metadata" in (e.tags or []) for e in evidence):
        return evidence
    refs: List[str] = []
    for e in evidence:
        if e.kind != "build":
            continue
        refs = (e.top_signals or {}).get("build_refs") or []
        if refs:
            break
    if not refs:
        return evidence
    build_provider = registry.get(build_id)
    try:
        meta = build_provider.get_build_metadata(refs[0])
        evidence.append(meta)
    except Exception:
        pass
    return evidence

def _call_query_logs(args: Dict[str, Any], incident: IncidentInput, subject_cfg: Dict[str, Any], registry):
    log_provider_id = subject_cfg["bindings"]["log_store"]
    log_provider = registry.get(log_provider_id)
    log_cfg = subject_cfg.get("log_evidence", {})
    selectors = (log_cfg.get("stream_selectors") or {})
    parse_cfg = (log_cfg.get("parse") or {})
    default_filters = (log_cfg.get("default_filters") or {})
    filters = default_filters.copy()
    for expr in args.get("filter_expressions") or []:
        if "=" in expr:
            k, v = expr.split("=", 1)
            filters[k.strip()] = v.strip()
    req = LogQueryRequest(
        subject=incident.subject,
        environment=incident.environment,
        time_range=incident.time_range,
        intent=args.get("intent", "samples"),
        stream_selectors=selectors,
        parse=parse_cfg,
        filters=filters,
        limit=int(args.get("limit") or 200),
    )
    return log_provider.query(req)

def _call_query_k8s_logs(args: Dict[str, Any], incident: IncidentInput, subject_cfg: Dict[str, Any], registry):
    runtime_id = subject_cfg["bindings"].get("runtime")
    if not runtime_id:
        return None
    runtime = registry.get(runtime_id)
    req = K8sLogQueryRequest(
        subject=incident.subject,
        environment=incident.environment,
        time_range=incident.time_range,
        namespace=args.get("namespace"),
        selector=args.get("selector"),
        container=args.get("container"),
        limit=int(args.get("limit") or 200),
    )
    return runtime.get_logs(req)

def _call_list_k8s_events(args: Dict[str, Any], incident: IncidentInput, subject_cfg: Dict[str, Any], registry):
    runtime_id = subject_cfg["bindings"].get("runtime")
    if not runtime_id:
        return None
    runtime = registry.get(runtime_id)
    req = EventQueryRequest(
        subject=incident.subject,
        environment=incident.environment,
        time_range=incident.time_range,
        namespace=args.get("namespace"),
        selector=args.get("selector"),
        limit=int(args.get("limit") or 200),
    )
    return runtime.get_events(req)

def _call_list_deployments(args: Dict[str, Any], incident: IncidentInput, subject_cfg: Dict[str, Any], registry):
    deploy_id = subject_cfg["bindings"].get("deploy_tracker")
    if not deploy_id:
        return None
    deploy_provider = registry.get(deploy_id)
    before = int(args.get("window_minutes_before") or 30)
    after = int(args.get("window_minutes_after") or 30)
    start = _shift_rfc3339(incident.time_range.start, -before)
    end = _shift_rfc3339(incident.time_range.end, +after)
    tr = TimeRange(start=start, end=end)
    req = DeployQueryRequest(
        subject=incident.subject,
        environment=incident.environment,
        time_range=tr,
        limit=int(args.get("limit") or 20),
    )
    return deploy_provider.list_deployments(req)

def _call_get_deployment_metadata(args: Dict[str, Any], subject_cfg: Dict[str, Any], registry):
    deploy_id = subject_cfg["bindings"].get("deploy_tracker")
    if not deploy_id:
        return None
    deploy_provider = registry.get(deploy_id)
    ref = args.get("deployment_ref")
    if not ref:
        return None
    return deploy_provider.get_deployment_metadata(ref)

def _call_list_changes(args: Dict[str, Any], incident: IncidentInput, subject_cfg: Dict[str, Any], registry):
    vcs_id = subject_cfg["bindings"].get("vcs")
    if not vcs_id:
        return None
    vcs_provider = registry.get(vcs_id)
    before = int(args.get("window_minutes_before") or 360)
    start = _shift_rfc3339(incident.time_range.start, -before)
    tr = TimeRange(start=start, end=incident.time_range.end)
    req = ChangeQueryRequest(
        subject=incident.subject,
        environment=incident.environment,
        time_range=tr,
        include_prs=bool(args.get("include_prs", True)),
        include_commits=bool(args.get("include_commits", False)),
        limit=int(args.get("limit") or 30),
    )
    return vcs_provider.list_changes(req)

def _call_list_builds(args: Dict[str, Any], incident: IncidentInput, subject_cfg: Dict[str, Any], registry):
    build_id = subject_cfg["bindings"].get("build_tracker")
    if not build_id:
        return None
    build_provider = registry.get(build_id)
    before = int(args.get("window_minutes_before") or 60)
    after = int(args.get("window_minutes_after") or 60)
    start = _shift_rfc3339(incident.time_range.start, -before)
    end = _shift_rfc3339(incident.time_range.end, +after)
    tr = TimeRange(start=start, end=end)
    req = BuildQueryRequest(
        subject=incident.subject,
        environment=incident.environment,
        time_range=tr,
        limit=int(args.get("limit") or 20),
    )
    return build_provider.list_builds(req)

def _call_get_build_metadata(args: Dict[str, Any], subject_cfg: Dict[str, Any], registry):
    build_id = subject_cfg["bindings"].get("build_tracker")
    if not build_id:
        return None
    build_provider = registry.get(build_id)
    ref = args.get("build_ref")
    if not ref:
        return None
    return build_provider.get_build_metadata(ref)

def _call_query_metrics(args: Dict[str, Any], incident: IncidentInput, subject_cfg: Dict[str, Any], registry):
    metrics_id = subject_cfg["bindings"].get("metrics_store")
    if not metrics_id:
        return None
    metrics_provider = registry.get(metrics_id)
    query = args.get("query") or f'up{{service="{incident.subject}"}}'
    req = MetricsQueryRequest(
        subject=incident.subject,
        environment=incident.environment,
        time_range=incident.time_range,
        query=query,
        step_seconds=int(args.get("step_seconds") or 60),
        limit=int(args.get("limit") or 50),
    )
    return metrics_provider.query_range(req)

def _call_query_traces(args: Dict[str, Any], incident: IncidentInput, subject_cfg: Dict[str, Any], registry):
    trace_id = subject_cfg["bindings"].get("trace_store")
    if not trace_id:
        return None
    trace_provider = registry.get(trace_id)
    req = TraceQueryRequest(
        subject=incident.subject,
        environment=incident.environment,
        time_range=incident.time_range,
        service_name=args.get("service_name"),
        limit=int(args.get("limit") or 20),
    )
    return trace_provider.search_traces(req)


GRAPH = build_graph()

def run(webhook_payload: dict) -> dict:
    state = {"raw_webhook": webhook_payload}
    out = GRAPH.invoke(state)
    return out.get("report", out)

def run_incident(incident: IncidentInput) -> dict:
    state = {"incident": incident.model_dump()}
    out = GRAPH.invoke(state)
    return out.get("report", out)
