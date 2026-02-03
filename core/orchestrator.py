from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from langgraph.graph import StateGraph

from openai import OpenAI
from core.config import settings
from core.models import (
    AgentState, IncidentInput, EvidenceItem, Hypothesis, RCAReport,
    LogQueryRequest, DeployQueryRequest, ChangeQueryRequest, TimeRange
)
from core.prompts import SYSTEM_PROMPT, HYPOTHESIS_TASK
from core.scoring import rank

client = OpenAI(api_key=settings.openai_api_key)

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

    g.add_node("collect_log_evidence", collect_log_evidence)
    g.add_node("collect_deploy_evidence", collect_deploy_evidence)
    g.add_node("collect_change_evidence", collect_change_evidence)

    g.add_node("hypothesize", hypothesize)
    g.add_node("score_and_report", score_and_report)

    g.set_entry_point("normalize_incident")
    g.add_edge("normalize_incident", "load_kb_slice")
    g.add_edge("load_kb_slice", "seed_alert_evidence")

    g.add_edge("seed_alert_evidence", "collect_log_evidence")
    g.add_edge("collect_log_evidence", "collect_deploy_evidence")
    g.add_edge("collect_deploy_evidence", "collect_change_evidence")

    g.add_edge("collect_change_evidence", "hypothesize")
    g.add_edge("hypothesize", "score_and_report")

    return g.compile()

# ---- Nodes (core-neutral) ----

def normalize_incident(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Accepts a webhook payload and maps it into a vendor-neutral IncidentInput.
    This parser is intentionally tolerant and does not assume a specific alerting product.
    """
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

def collect_log_evidence(state: Dict[str, Any]) -> Dict[str, Any]:
    incident = IncidentInput(**state["incident"])
    subject_cfg = state["kb_slice"]["subject_cfg"]
    registry = state["_registry"]

    log_provider_id = subject_cfg["bindings"]["log_store"]
    log_provider = registry.get(log_provider_id)

    log_cfg = subject_cfg.get("log_evidence", {})
    selectors = (log_cfg.get("stream_selectors") or {})
    parse_cfg = (log_cfg.get("parse") or {})

    tr = incident.time_range

    req1 = LogQueryRequest(
        subject=incident.subject,
        environment=incident.environment,
        time_range=tr,
        intent="signature_counts",
        stream_selectors=selectors,
        parse=parse_cfg,
        filters={},
        limit=200,
    )
    req2 = LogQueryRequest(
        subject=incident.subject,
        environment=incident.environment,
        time_range=tr,
        intent="samples",
        stream_selectors=selectors,
        parse=parse_cfg,
        filters={},
        limit=80,
    )

    ev = [EvidenceItem(**x) for x in state.get("evidence", [])]
    ev.append(log_provider.query(req1))
    ev.append(log_provider.query(req2))
    state["evidence"] = [e.model_dump() for e in ev]
    return state

def collect_deploy_evidence(state: Dict[str, Any]) -> Dict[str, Any]:
    incident = IncidentInput(**state["incident"])
    subject_cfg = state["kb_slice"]["subject_cfg"]
    registry = state["_registry"]

    deploy_id = subject_cfg["bindings"].get("deploy_tracker")
    if not deploy_id:
        return state  # optional capability

    deploy_provider = registry.get(deploy_id)

    # Search near incident window (+/- buffer)
    start = _shift_rfc3339(incident.time_range.start, -30)
    end = _shift_rfc3339(incident.time_range.end, +30)
    tr = TimeRange(start=start, end=end)

    req = DeployQueryRequest(
        subject=incident.subject,
        environment=incident.environment,
        time_range=tr,
        limit=20,
    )

    ev = [EvidenceItem(**x) for x in state.get("evidence", [])]
    deployments = deploy_provider.list_deployments(req)
    ev.append(deployments)

    # If we have deployment references, fetch metadata for the closest 1
    refs = (deployments.top_signals or {}).get("deployment_refs", [])
    if refs:
        ev.append(deploy_provider.get_deployment_metadata(refs[0]))

    state["evidence"] = [e.model_dump() for e in ev]
    return state

def collect_change_evidence(state: Dict[str, Any]) -> Dict[str, Any]:
    incident = IncidentInput(**state["incident"])
    subject_cfg = state["kb_slice"]["subject_cfg"]
    registry = state["_registry"]

    vcs_id = subject_cfg["bindings"].get("vcs")
    if not vcs_id:
        return state

    vcs_provider = registry.get(vcs_id)

    # Buffered change window: start-6h to end
    start = _shift_rfc3339(incident.time_range.start, -360)
    tr = TimeRange(start=start, end=incident.time_range.end)

    req = ChangeQueryRequest(
        subject=incident.subject,
        environment=incident.environment,
        time_range=tr,
        include_prs=True,
        include_commits=False,
        limit=30,
    )

    ev = [EvidenceItem(**x) for x in state.get("evidence", [])]
    ev.append(vcs_provider.list_changes(req))
    state["evidence"] = [e.model_dump() for e in ev]
    return state

def hypothesize(state: Dict[str, Any]) -> Dict[str, Any]:
    incident = IncidentInput(**state["incident"])
    evidence = [EvidenceItem(**x) for x in state.get("evidence", [])]
    subject_cfg = state["kb_slice"]["subject_cfg"]

    # compact evidence for LLM
    compact = []
    for e in evidence:
        compact.append({
            "id": e.id,
            "kind": e.kind,
            "summary": e.summary,
            "top_signals": e.top_signals,
            "sample_preview": e.samples[:8],
        })

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
    return state


GRAPH = build_graph()

def run(webhook_payload: dict) -> dict:
    state = {"raw_webhook": webhook_payload}
    out = GRAPH.invoke(state)
    return out.get("report", out)