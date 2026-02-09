from typing import Any, Dict, List, Optional, Literal, Set
from datetime import datetime, timezone
from pathlib import Path
import difflib
import yaml

from fastapi import FastAPI, HTTPException, Query, Request
from sqlalchemy import desc, func, select
from pydantic import BaseModel, Field, field_validator

from core.models import IncidentInput, TimeRange, RCAReport
from core.environment import canonicalize_environment
from core.orchestrator import run, run_incident, _now_rfc3339, _shift_rfc3339
from core.persistence import (
    bootstrap,
    create_action_execution,
    persistence_enabled,
    record_audit,
    save_report,
    update_action_status,
)
from core.db import get_db
from core.persistence_models import ActionExecution, AuditEvent, EvidenceItem, Incident, IncidentReport
from core.kb import KB
from core.config import settings
from core.onboarding_agent import apply_ops as apply_onboarding_ops
from core.onboarding_agent import plan_ops as plan_onboarding_ops

app = FastAPI(title="RCA Investigation Agent")
LAST_REPORT: Optional[RCAReport] = None


def _demo_incidents() -> List[Dict[str, Any]]:
    return [
        {
            "id": "inc-1842",
            "title": "Payment latency spike in us-west-2",
            "severity": "P1",
            "environment": "prod",
            "status": "investigation",
            "updated": "2m ago",
        },
        {
            "id": "inc-1836",
            "title": "Auth token refresh failures",
            "severity": "P2",
            "environment": "prod",
            "status": "steady_state",
            "updated": "14m ago",
        },
        {
            "id": "inc-1829",
            "title": "Terraform drift detected in staging",
            "severity": "P3",
            "environment": "staging",
            "status": "review",
            "updated": "1h ago",
        },
    ]

def _demo_enabled() -> bool:
    return bool(settings.show_demo_data)


def _demo_timeline() -> List[Dict[str, Any]]:
    return [
        {
            "time": "02:10 UTC",
            "label": "Deploy v2026.02.03.4 completed",
            "source": "GitHub Actions",
        },
        {
            "time": "02:12 UTC",
            "label": "5xx error rate increased to 4.2%",
            "source": "Prometheus",
        },
        {
            "time": "02:13 UTC",
            "label": "Trace failures detected in payments-api",
            "source": "Tempo",
        },
        {
            "time": "02:15 UTC",
            "label": "Customer impact reported by support",
            "source": "Incident feed",
        },
    ]


def _demo_hypotheses() -> List[Dict[str, Any]]:
    return [
        {
            "id": "hyp-1",
            "statement": "Deploy v2026.02.03.4 introduced connection pool exhaustion.",
            "confidence": 0.71,
            "evidence": ["Loki error signature spike", "Tempo trace failures", "Deploy event at 02:10 UTC"],
        },
        {
            "id": "hyp-2",
            "statement": "Regional node pressure causing transient timeouts.",
            "confidence": 0.48,
            "evidence": ["Kubernetes events show node pressure", "Latency isolated to us-west-2"],
        },
        {
            "id": "hyp-3",
            "statement": "Auth service regression after Terraform apply.",
            "confidence": 0.37,
            "evidence": ["Terraform apply 01:55 UTC", "Auth error logs 01:57 UTC"],
        },
    ]


def _demo_actions() -> List[Dict[str, Any]]:
    return [
        {"id": "act-1", "name": "Rollback payments-api to v2026.02.02.9", "risk": "Medium", "requires_approval": True},
        {"id": "act-2", "name": "Scale payments-api replicas +2", "risk": "Low", "requires_approval": False},
        {"id": "act-3", "name": "Disable rate limiter for 15 minutes", "risk": "High", "requires_approval": True},
    ]

def _parse_rfc3339(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

@app.get("/health")
def health():
    return {"ok": True}


@app.get("/ui/mode")
def ui_mode():
    return {"live_mode": settings.live_mode}


@app.on_event("startup")
def _startup():
    bootstrap()

@app.post("/webhook")
async def webhook(req: Request):
    payload = await req.json()
    return run(payload)


class IncidentWebhookRequest(BaseModel):
    title: str = Field(..., description="Human-readable incident title")
    severity: str
    environment: str
    subject: str
    starts_at: Optional[str] = Field(None, description="RFC3339 start time")
    ends_at: Optional[str] = Field(None, description="RFC3339 end time")
    labels: Dict[str, str] = Field(default_factory=dict)
    annotations: Dict[str, str] = Field(default_factory=dict)
    raw: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("subject", "environment", "severity", "title")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must be non-empty")
        return v


@app.post("/webhook/incident")
def webhook_incident(payload: IncidentWebhookRequest):
    ends_at = payload.ends_at or _now_rfc3339()
    starts_at = payload.starts_at or _shift_rfc3339(ends_at, -60)

    tr = TimeRange(start=_shift_rfc3339(starts_at, -10), end=ends_at)
    environment = canonicalize_environment(payload.environment)
    incident = IncidentInput(
        title=payload.title,
        severity=payload.severity,
        environment=environment,
        subject=payload.subject,
        time_range=tr,
        labels=payload.labels,
        annotations=payload.annotations,
        raw=payload.raw,
    )
    global LAST_REPORT
    report_dict = run_incident(incident)
    try:
        LAST_REPORT = RCAReport.model_validate(report_dict)
    except Exception:
        LAST_REPORT = None
    if LAST_REPORT:
        save_report(incident, LAST_REPORT)
    return report_dict


@app.get("/ui/incidents")
def list_incidents():
    if LAST_REPORT:
        return [
            {
                "id": "inc-current",
                "title": LAST_REPORT.incident_summary,
                "severity": "P1",
                "environment": "prod",
                "status": "investigation",
                "updated": "just now",
                "time_range": LAST_REPORT.time_range.model_dump(),
            }
        ]
    return _demo_incidents() if _demo_enabled() else []


@app.get("/ui/incidents/{incident_id}/timeline")
def incident_timeline(incident_id: str):
    if LAST_REPORT:
        timeline = []
        for item in LAST_REPORT.evidence:
            timeline.append(
                {
                    "time": item.time_range.start,
                    "label": item.summary,
                    "source": item.source,
                    "kind": item.kind,
                }
            )
        return timeline
    return _demo_timeline() if _demo_enabled() else []


@app.get("/ui/incidents/{incident_id}/hypotheses")
def incident_hypotheses(incident_id: str):
    if LAST_REPORT:
        hypotheses = [
            {
                "id": LAST_REPORT.top_hypothesis.id,
                "statement": LAST_REPORT.top_hypothesis.statement,
                "confidence": LAST_REPORT.top_hypothesis.confidence,
                "evidence_ids": LAST_REPORT.top_hypothesis.supporting_evidence_ids,
                "validations": LAST_REPORT.top_hypothesis.validations,
            }
        ]
        for hyp in LAST_REPORT.other_hypotheses:
            hypotheses.append(
                {
                    "id": hyp.id,
                    "statement": hyp.statement,
                    "confidence": hyp.confidence,
                    "evidence_ids": hyp.supporting_evidence_ids,
                    "validations": hyp.validations,
                }
            )
        return hypotheses
    return _demo_hypotheses() if _demo_enabled() else []


@app.get("/ui/actions")
def list_actions():
    if LAST_REPORT:
        actions = []
        for idx, validation in enumerate(LAST_REPORT.next_validations, start=1):
            actions.append(
                {
                    "id": f"act-{idx}",
                    "name": validation,
                    "risk": "Low",
                    "requires_approval": True,
                    "intent": "validation",
                }
            )
        if actions:
            return actions
    return _demo_actions() if _demo_enabled() else []


def _latest_report_from_db() -> Optional[IncidentReport]:
    with get_db() as db:
        return (
            db.execute(select(IncidentReport).order_by(desc(IncidentReport.created_at)).limit(1))
            .scalars()
            .first()
        )


def _summary_from_report(report: dict | None) -> dict:
    if not report:
        return {
            "summary": "No RCA report available yet.",
            "confidence": None,
            "citations": [],
        }
    top = report.get("top_hypothesis", {})
    return {
        "summary": report.get("incident_summary", "RCA report"),
        "confidence": top.get("confidence"),
        "citations": top.get("supporting_evidence_ids", []),
    }


@app.get("/ui/summary")
def ui_summary():
    if persistence_enabled():
        latest = _latest_report_from_db()
        if latest:
            return _summary_from_report(latest.report)
    if LAST_REPORT:
        return _summary_from_report(LAST_REPORT.model_dump())
    return _summary_from_report(None)


@app.get("/ui/attention")
def ui_attention(limit: int = Query(5, ge=1, le=20)):
    if persistence_enabled():
        with get_db() as db:
            rows = (
                db.execute(select(Incident).order_by(desc(Incident.created_at)).limit(limit))
                .scalars()
                .all()
            )
            return [
                {
                    "id": row.id,
                    "title": row.title,
                    "severity": row.severity,
                    "environment": row.environment,
                    "updated_at": row.updated_at.isoformat(),
                }
                for row in rows
            ]
    if LAST_REPORT:
        return [
            {
                "id": "inc-current",
                "title": LAST_REPORT.incident_summary,
                "severity": "P1",
                "environment": "prod",
                "updated_at": "just now",
            }
        ]
    return []


@app.get("/signals/timeline")
def signals_timeline(incident_id: Optional[str] = None):
    if persistence_enabled():
        with get_db() as db:
            report = None
            if incident_id:
                report = (
                    db.execute(
                        select(IncidentReport)
                        .where(IncidentReport.incident_id == incident_id)
                        .order_by(desc(IncidentReport.created_at))
                        .limit(1)
                    )
                    .scalars()
                    .first()
                )
            if not report:
                report = _latest_report_from_db()
            if report and report.report:
                evidence = report.report.get("evidence", [])
                return [
                    {
                        "time": item.get("time_range", {}).get("start"),
                        "label": item.get("summary"),
                        "source": item.get("source"),
                        "kind": item.get("kind"),
                    }
                    for item in evidence
                ]
    if LAST_REPORT:
        return [
            {
                "time": item.time_range.start,
                "label": item.summary,
                "source": item.source,
                "kind": item.kind,
            }
            for item in LAST_REPORT.evidence
        ]
    return _demo_timeline() if _demo_enabled() else []


@app.get("/signals/correlation")
def signals_correlation(incident_id: Optional[str] = None):
    timeline = signals_timeline(incident_id)
    kinds = {}
    for item in timeline:
        kind = item.get("kind") or "unknown"
        kinds[kind] = kinds.get(kind, 0) + 1
    pairs = []
    for kind, count in kinds.items():
        pairs.append({"pair": f"{kind}→signals", "score": min(1.0, 0.2 + 0.1 * count)})
    return {"pairs": pairs}


@app.get("/incidents/{incident_id}/changes")
def incident_changes(incident_id: str):
    if persistence_enabled():
        with get_db() as db:
            report = (
                db.execute(
                    select(IncidentReport)
                    .where(IncidentReport.incident_id == incident_id)
                    .order_by(desc(IncidentReport.created_at))
                    .limit(1)
                )
                .scalars()
                .first()
            )
            if report and report.report:
                evidence = report.report.get("evidence", [])
                return [
                    item
                    for item in evidence
                    if item.get("kind") in ("deployment", "change", "build")
                ]
    return []


@app.get("/incidents/{incident_id}/alerts")
def incident_alerts(incident_id: str):
    if persistence_enabled():
        with get_db() as db:
            report = (
                db.execute(
                    select(IncidentReport)
                    .where(IncidentReport.incident_id == incident_id)
                    .order_by(desc(IncidentReport.created_at))
                    .limit(1)
                )
                .scalars()
                .first()
            )
            if report and report.report:
                evidence = report.report.get("evidence", [])
                return [
                    item
                    for item in evidence
                    if item.get("kind") in ("alert", "event", "metric")
                ]
    return []


@app.get("/knowledge/runbooks")
def knowledge_runbooks():
    kb = KB.load(settings.kb_path)
    subjects = kb.raw.get("subjects", [])
    runbooks = []
    for s in subjects:
        for mode in s.get("known_failure_modes", []) or []:
            runbooks.append(
                {
                    "subject": s.get("name"),
                    "name": f"rbk-{s.get('name')}-{mode.get('name')}",
                    "indicators": mode.get("indicators", []),
                }
            )
    return runbooks


@app.get("/knowledge/patterns")
def knowledge_patterns():
    kb = KB.load(settings.kb_path)
    subjects = kb.raw.get("subjects", [])
    patterns = []
    for s in subjects:
        for mode in s.get("known_failure_modes", []) or []:
            patterns.append(
                {
                    "subject": s.get("name"),
                    "pattern": mode.get("name"),
                    "indicators": mode.get("indicators", []),
                }
            )
    return patterns


@app.get("/knowledge/incidents")
def knowledge_incidents(limit: int = Query(20, ge=1, le=100)):
    if persistence_enabled():
        with get_db() as db:
            rows = (
                db.execute(select(Incident).order_by(desc(Incident.created_at)).limit(limit))
                .scalars()
                .all()
            )
            return [
                {
                    "id": row.id,
                    "title": row.title,
                    "severity": row.severity,
                    "environment": row.environment,
                    "subject": row.subject,
                    "created_at": row.created_at.isoformat(),
                }
                for row in rows
            ]
    return []


def _redact_provider_config(config: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(config, dict):
        return {}
    # Configs only contain env var names; keep structure but avoid any secret values.
    redacted: Dict[str, Any] = {}
    for key, value in config.items():
        if isinstance(value, dict):
            redacted[key] = _redact_provider_config(value)
        else:
            redacted[key] = value
    return redacted


@app.get("/knowledge/onboarding")
def knowledge_onboarding():
    kb = KB.load(settings.kb_path)
    providers = KB.load_providers(settings.catalog_path)
    provider_list = []
    for pid, cfg in providers.items():
        provider_list.append(
            {
                "id": pid,
                "category": cfg.get("category"),
                "type": cfg.get("type"),
                "capabilities": cfg.get("capabilities", {}),
                "config": _redact_provider_config(cfg.get("config", {})),
            }
        )
    return {
        "subjects": kb.raw.get("subjects", []),
        "providers": provider_list,
        "catalog_path": settings.catalog_path,
        "kb_path": settings.kb_path,
    }


def _load_yaml_text(label: str, text: str) -> Dict[str, Any]:
    try:
        data = yaml.safe_load(text) if text.strip() else {}
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail=f"{label} YAML parse error: {exc}") from exc
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail=f"{label} YAML must be a mapping/object at top level.")
    return data


_CATEGORY_TO_CAPABILITY_TYPES: Dict[str, List[str]] = {
    "log_store": ["logs"],
    "metrics_store": ["metrics"],
    "trace_store": ["traces"],
    "alerting": ["alerts"],
    "deploy_tracker": ["deployments", "pipelines"],
    "build_tracker": ["pipelines"],
    "vcs": ["changes"],
    "runtime": ["workloads", "nodes"],
}

_LEGACY_OP_ALIASES: Dict[str, str] = {
    "query.samples": "search",
    "query.signature_counts": "aggregate",
    "query_range": "timeseries_query",
    "search_traces": "search",
    "list_alerts": "list",
    "list_deployments": "list",
    "get_deployment_metadata": "get",
    "list_changes": "list_prs",
}


def _load_rca_tools_schema_doc() -> Dict[str, Any]:
    schema_path = Path(settings.rca_tools_schema_path)
    if not schema_path.exists():
        return {}
    raw = schema_path.read_text()
    try:
        parsed = yaml.safe_load(raw) if raw.strip() else {}
    except yaml.YAMLError:
        # Some sections in the human-readable schema file may use non-YAML type shorthand
        # (e.g. list[string]). We only need tool_catalog for onboarding provider validation.
        marker = "\ntool_catalog:"
        start = raw.find(marker)
        if start < 0:
            return {}
        tail = raw[start + 1 :]
        end_marker = "\n# -----------------------------\n# 4)"
        end = tail.find(end_marker)
        tool_catalog_fragment = tail if end < 0 else tail[:end]
        try:
            parsed_fragment = yaml.safe_load(tool_catalog_fragment)
        except yaml.YAMLError:
            return {}
        if not isinstance(parsed_fragment, dict):
            return {}
        return {"tool_catalog": parsed_fragment.get("tool_catalog", {})}
    if parsed is None:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _schema_allowed_operations_by_capability(schema_doc: Dict[str, Any]) -> Dict[str, Set[str]]:
    by_capability: Dict[str, Set[str]] = {}
    tools = (schema_doc.get("tool_catalog") or {}).get("tools") or []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        capabilities = tool.get("capabilities") or {}
        for mode in ("read", "write", "execute"):
            entries = capabilities.get(mode) or []
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                cap_type = entry.get("type")
                operations = entry.get("operations") or []
                if not isinstance(cap_type, str) or not isinstance(operations, list):
                    continue
                by_capability.setdefault(cap_type, set()).update(
                    op for op in operations if isinstance(op, str) and op
                )
    return by_capability


def _validate_catalog_against_rca_schema(catalog_doc: Dict[str, Any]) -> List[str]:
    schema_doc = _load_rca_tools_schema_doc()
    if not schema_doc:
        return []

    allowed_ops_by_capability = _schema_allowed_operations_by_capability(schema_doc)
    if not allowed_ops_by_capability:
        return ["RCA tools schema has no declared capability operations under tool_catalog.tools."]

    errors: List[str] = []
    providers = catalog_doc.get("providers", [])
    for provider in providers:
        if not isinstance(provider, dict):
            continue
        provider_id = provider.get("id", "<missing-id>")
        category = provider.get("category")
        if not isinstance(category, str) or not category:
            errors.append(f"[provider:{provider_id}] missing category")
            continue

        capability_types = _CATEGORY_TO_CAPABILITY_TYPES.get(category)
        if not capability_types:
            errors.append(
                f"[provider:{provider_id}] unknown category '{category}' not mapped in RCA schema validator"
            )
            continue

        allowed_ops: Set[str] = set()
        for cap_type in capability_types:
            allowed_ops.update(allowed_ops_by_capability.get(cap_type, set()))
        if not allowed_ops:
            errors.append(
                f"[provider:{provider_id}] category '{category}' has no matching capability ops in RCA tools schema"
            )
            continue

        operations = ((provider.get("capabilities") or {}).get("operations")) or []
        if not isinstance(operations, list):
            errors.append(f"[provider:{provider_id}] capabilities.operations must be a list")
            continue

        for operation in operations:
            if not isinstance(operation, str) or not operation:
                errors.append(f"[provider:{provider_id}] contains non-string operation entry")
                continue
            canonical = _LEGACY_OP_ALIASES.get(operation, operation)
            if canonical not in allowed_ops:
                allowed_display = ", ".join(sorted(allowed_ops))
                errors.append(
                    f"[provider:{provider_id}] operation '{operation}' is not allowed for category '{category}'. "
                    f"Allowed: {allowed_display}"
                )

    return errors


def _validate_kb_docs(subjects_doc: Dict[str, Any], catalog_doc: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    providers = {
        p["id"]: p
        for p in catalog_doc.get("providers", [])
        if isinstance(p, dict) and "id" in p
    }
    if not providers:
        errors.append("No providers found in catalog YAML.")

    subjects = subjects_doc.get("subjects", [])
    if not subjects:
        errors.append("No subjects found in subjects YAML.")

    for s in subjects:
        name = s.get("name", "<missing-name>")
        bindings = s.get("bindings") or {}

        for cap, pid in bindings.items():
            if not isinstance(pid, str) or not pid:
                errors.append(f"[{name}] binding '{cap}' must be a non-empty string")
                continue
            if pid not in providers:
                errors.append(f"[{name}] binding '{cap}' references missing provider id '{pid}'")

        log_ev = s.get("log_evidence") or {}
        parse = log_ev.get("parse") or {}
        fmt = parse.get("format")
        fields = parse.get("fields") or {}

        if fmt == "json":
            for req_field in ("env", "err_msg"):
                if req_field not in fields or not isinstance(fields.get(req_field), str) or not fields.get(req_field).strip():
                    errors.append(f"[{name}] log_evidence.parse.fields must include non-empty '{req_field}' for json logs")

    errors.extend(_validate_catalog_against_rca_schema(catalog_doc))

    return errors


class OnboardingYamlRequest(BaseModel):
    catalog_yaml: str = Field(..., description="Catalog YAML (instances)")
    kb_yaml: str = Field(..., description="Knowledge base YAML (subjects)")


class OnboardingProviderModel(BaseModel):
    id: str
    category: str
    type: str
    operations: List[str] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)


class OnboardingFailureModeModel(BaseModel):
    name: str
    indicators: List[str] = Field(default_factory=list)


class OnboardingSubjectModel(BaseModel):
    name: str
    environment: str = "prod"
    aliases: List[str] = Field(default_factory=list)
    bindings: Dict[str, str] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    runbooks: List[str] = Field(default_factory=list)
    known_failure_modes: List[OnboardingFailureModeModel] = Field(default_factory=list)
    deploy_context: Dict[str, Any] = Field(default_factory=dict)
    vcs_context: Dict[str, Any] = Field(default_factory=dict)
    log_evidence: Dict[str, Any] = Field(default_factory=dict)


class OnboardingModel(BaseModel):
    providers: List[OnboardingProviderModel] = Field(default_factory=list)
    subjects: List[OnboardingSubjectModel] = Field(default_factory=list)


class OnboardingModelRequest(BaseModel):
    model: OnboardingModel


class OnboardingAgentOp(BaseModel):
    type: Literal["add_provider", "add_subject", "bind_subject_provider"]
    provider: Optional[Dict[str, Any]] = None
    subject: Optional[Dict[str, Any]] = None
    binding: Optional[Dict[str, Any]] = None


class OnboardingAgentPlanRequest(BaseModel):
    intent: str
    model: OnboardingModel
    policy: Dict[str, Any] = Field(default_factory=dict)


class OnboardingAgentApplyRequest(BaseModel):
    model: OnboardingModel
    ops: List[OnboardingAgentOp] = Field(default_factory=list)
    policy: Dict[str, Any] = Field(default_factory=dict)


def _normalize_provider_model(provider: Dict[str, Any]) -> Dict[str, Any]:
    capabilities = provider.get("capabilities") or {}
    operations = capabilities.get("operations") if isinstance(capabilities, dict) else []
    if not isinstance(operations, list):
        operations = []
    return {
        "id": provider.get("id", ""),
        "category": provider.get("category", ""),
        "type": provider.get("type", ""),
        "operations": [str(op) for op in operations if isinstance(op, str)],
        "config": provider.get("config", {}) if isinstance(provider.get("config"), dict) else {},
    }


def _normalize_subject_model(subject: Dict[str, Any]) -> Dict[str, Any]:
    known_modes = subject.get("known_failure_modes") or []
    normalized_modes: List[Dict[str, Any]] = []
    for mode in known_modes:
        if isinstance(mode, dict):
            normalized_modes.append(
                {
                    "name": mode.get("name", ""),
                    "indicators": mode.get("indicators", []) if isinstance(mode.get("indicators"), list) else [],
                }
            )
    return {
        "name": subject.get("name", ""),
        "environment": subject.get("environment", "prod"),
        "aliases": subject.get("aliases", []) if isinstance(subject.get("aliases"), list) else [],
        "bindings": subject.get("bindings", {}) if isinstance(subject.get("bindings"), dict) else {},
        "dependencies": subject.get("dependencies", []) if isinstance(subject.get("dependencies"), list) else [],
        "runbooks": subject.get("runbooks", []) if isinstance(subject.get("runbooks"), list) else [],
        "known_failure_modes": normalized_modes,
        "deploy_context": subject.get("deploy_context", {}) if isinstance(subject.get("deploy_context"), dict) else {},
        "vcs_context": subject.get("vcs_context", {}) if isinstance(subject.get("vcs_context"), dict) else {},
        "log_evidence": subject.get("log_evidence", {}) if isinstance(subject.get("log_evidence"), dict) else {},
    }


def _model_from_docs(catalog_doc: Dict[str, Any], kb_doc: Dict[str, Any]) -> OnboardingModel:
    providers = [_normalize_provider_model(p) for p in catalog_doc.get("providers", []) if isinstance(p, dict)]
    subjects = [_normalize_subject_model(s) for s in kb_doc.get("subjects", []) if isinstance(s, dict)]
    return OnboardingModel.model_validate({"providers": providers, "subjects": subjects})


def _docs_from_model(model: OnboardingModel) -> Dict[str, Dict[str, Any]]:
    providers = []
    for provider in model.providers:
        providers.append(
            {
                "id": provider.id,
                "category": provider.category,
                "type": provider.type,
                "capabilities": {"operations": provider.operations},
                "config": provider.config,
            }
        )

    subjects = []
    for subject in model.subjects:
        subjects.append(
            {
                "name": subject.name,
                "environment": subject.environment,
                "aliases": subject.aliases,
                "bindings": subject.bindings,
                "log_evidence": subject.log_evidence,
                "deploy_context": subject.deploy_context,
                "vcs_context": subject.vcs_context,
                "known_failure_modes": [mode.model_dump() for mode in subject.known_failure_modes],
                "dependencies": subject.dependencies,
                "runbooks": subject.runbooks,
            }
        )

    return {
        "catalog": {"version": 1, "providers": providers},
        "kb": {"version": 1, "subjects": subjects},
    }


def _yaml_from_docs(catalog_doc: Dict[str, Any], kb_doc: Dict[str, Any]) -> Dict[str, str]:
    return {
        "catalog": yaml.safe_dump(catalog_doc, sort_keys=False),
        "kb": yaml.safe_dump(kb_doc, sort_keys=False),
    }


def _resolved_bindings(model: OnboardingModel) -> List[Dict[str, Any]]:
    provider_map = {provider.id: provider for provider in model.providers}
    out: List[Dict[str, Any]] = []
    for subject in model.subjects:
        bindings = []
        for capability, provider_id in subject.bindings.items():
            provider = provider_map.get(provider_id)
            bindings.append(
                {
                    "capability": capability,
                    "provider_id": provider_id,
                    "resolved": provider is not None,
                    "provider_category": provider.category if provider else None,
                    "provider_type": provider.type if provider else None,
                }
            )
        out.append(
            {
                "subject": subject.name,
                "environment": subject.environment,
                "bindings": bindings,
            }
        )
    return out


def _onboarding_diffs(catalog_yaml: str, kb_yaml: str) -> Dict[str, str]:
    current_catalog = Path(settings.catalog_path).read_text()
    current_kb = Path(settings.kb_path).read_text()
    catalog_diff = "\n".join(
        difflib.unified_diff(
            current_catalog.splitlines(),
            catalog_yaml.splitlines(),
            fromfile=settings.catalog_path,
            tofile=f"{settings.catalog_path} (proposed)",
            lineterm="",
        )
    )
    kb_diff = "\n".join(
        difflib.unified_diff(
            current_kb.splitlines(),
            kb_yaml.splitlines(),
            fromfile=settings.kb_path,
            tofile=f"{settings.kb_path} (proposed)",
            lineterm="",
        )
    )
    return {"catalog": catalog_diff, "kb": kb_diff}


def _resolve_onboarding_profile(profile: Optional[str]) -> str:
    resolved = (profile or settings.onboarding_profile or "template").strip().lower()
    return resolved if resolved in {"template", "demo"} else "template"


def _load_profile_docs(profile: str) -> Dict[str, Dict[str, Any]]:
    if profile == "demo":
        catalog_path = Path(settings.onboarding_demo_catalog_path)
        kb_path = Path(settings.onboarding_demo_kb_path)
    else:
        catalog_path = Path(settings.onboarding_template_catalog_path)
        kb_path = Path(settings.onboarding_template_kb_path)

    if not catalog_path.exists() or not kb_path.exists():
        # Fallback to active writable files if seeds are missing.
        return {
            "catalog": _load_yaml_text("Catalog", Path(settings.catalog_path).read_text()),
            "kb": _load_yaml_text("Knowledge base", Path(settings.kb_path).read_text()),
            "source_catalog_path": settings.catalog_path,
            "source_kb_path": settings.kb_path,
        }

    return {
        "catalog": _load_yaml_text("Catalog", catalog_path.read_text()),
        "kb": _load_yaml_text("Knowledge base", kb_path.read_text()),
        "source_catalog_path": str(catalog_path),
        "source_kb_path": str(kb_path),
    }


@app.get("/knowledge/onboarding/raw")
def knowledge_onboarding_raw():
    catalog_text = Path(settings.catalog_path).read_text()
    kb_text = Path(settings.kb_path).read_text()
    return {
        "catalog_yaml": catalog_text,
        "kb_yaml": kb_text,
        "catalog_path": settings.catalog_path,
        "kb_path": settings.kb_path,
    }


@app.get("/knowledge/onboarding/model")
def knowledge_onboarding_model(profile: Optional[str] = Query(default=None)):
    resolved_profile = _resolve_onboarding_profile(profile)
    docs = _load_profile_docs(resolved_profile)
    model = _model_from_docs(docs["catalog"], docs["kb"])
    categories = sorted({provider.category for provider in model.providers if provider.category})
    return {
        "model": model.model_dump(),
        "resolved_bindings": _resolved_bindings(model),
        "available_binding_capabilities": categories,
        "profile": resolved_profile,
        "source_catalog_path": docs["source_catalog_path"],
        "source_kb_path": docs["source_kb_path"],
        "catalog_path": settings.catalog_path,
        "kb_path": settings.kb_path,
    }


@app.post("/knowledge/onboarding/preview")
def knowledge_onboarding_preview(payload: OnboardingYamlRequest):
    catalog_doc = _load_yaml_text("Catalog", payload.catalog_yaml)
    kb_doc = _load_yaml_text("Knowledge base", payload.kb_yaml)
    errors = _validate_kb_docs(kb_doc, catalog_doc)
    model = _model_from_docs(catalog_doc, kb_doc)

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "diffs": _onboarding_diffs(payload.catalog_yaml, payload.kb_yaml),
        "resolved_bindings": _resolved_bindings(model),
        "model": model.model_dump(),
    }


@app.post("/knowledge/onboarding/validate")
def knowledge_onboarding_validate(payload: OnboardingYamlRequest):
    catalog_doc = _load_yaml_text("Catalog", payload.catalog_yaml)
    kb_doc = _load_yaml_text("Knowledge base", payload.kb_yaml)
    errors = _validate_kb_docs(kb_doc, catalog_doc)
    return {"ok": len(errors) == 0, "errors": errors}


@app.post("/knowledge/onboarding/model/preview")
def knowledge_onboarding_model_preview(payload: OnboardingModelRequest):
    docs = _docs_from_model(payload.model)
    yamls = _yaml_from_docs(docs["catalog"], docs["kb"])
    errors = _validate_kb_docs(docs["kb"], docs["catalog"])
    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "yaml": {
            "catalog_yaml": yamls["catalog"],
            "kb_yaml": yamls["kb"],
        },
        "diffs": _onboarding_diffs(yamls["catalog"], yamls["kb"]),
        "resolved_bindings": _resolved_bindings(payload.model),
    }


@app.post("/knowledge/onboarding/agent/plan")
def knowledge_onboarding_agent_plan(payload: OnboardingAgentPlanRequest):
    plan = plan_onboarding_ops(
        intent=payload.intent,
        model=payload.model.model_dump(),
        policy_raw=payload.policy,
    )
    preview_model = OnboardingModel.model_validate(plan["preview_model"])
    return {
        "proposed_ops": plan["proposed_ops"],
        "preview_model": preview_model.model_dump(),
        "warnings": plan["warnings"],
        "requires_confirmation": plan["requires_confirmation"],
        "applied_ops": plan["applied_ops"],
        "rejected_ops": plan["rejected_ops"],
        "resolved_bindings": _resolved_bindings(preview_model),
    }


@app.post("/knowledge/onboarding/agent/apply-ops")
def knowledge_onboarding_agent_apply_ops(payload: OnboardingAgentApplyRequest):
    ops_payload = [op.model_dump(exclude_none=True) for op in payload.ops]
    next_model, applied_ops, rejected_ops, warnings = apply_onboarding_ops(
        model=payload.model.model_dump(),
        ops=ops_payload,
        policy_raw=payload.policy,
    )
    validated = OnboardingModel.model_validate(next_model)
    return {
        "model": validated.model_dump(),
        "warnings": warnings,
        "applied_ops": applied_ops,
        "rejected_ops": rejected_ops,
        "resolved_bindings": _resolved_bindings(validated),
    }


@app.post("/knowledge/onboarding/apply")
def knowledge_onboarding_apply(payload: OnboardingYamlRequest):
    catalog_doc = _load_yaml_text("Catalog", payload.catalog_yaml)
    kb_doc = _load_yaml_text("Knowledge base", payload.kb_yaml)
    errors = _validate_kb_docs(kb_doc, catalog_doc)
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})

    now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    catalog_path = Path(settings.catalog_path)
    kb_path = Path(settings.kb_path)
    catalog_backup = catalog_path.with_suffix(catalog_path.suffix + f".bak.{now}")
    kb_backup = kb_path.with_suffix(kb_path.suffix + f".bak.{now}")
    catalog_backup.write_text(catalog_path.read_text())
    kb_backup.write_text(kb_path.read_text())
    catalog_path.write_text(payload.catalog_yaml)
    kb_path.write_text(payload.kb_yaml)

    return {
        "ok": True,
        "catalog_path": settings.catalog_path,
        "kb_path": settings.kb_path,
        "backup_paths": {
            "catalog": str(catalog_backup),
            "kb": str(kb_backup),
        },
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }


@app.post("/knowledge/onboarding/model/apply")
def knowledge_onboarding_model_apply(payload: OnboardingModelRequest):
    docs = _docs_from_model(payload.model)
    yamls = _yaml_from_docs(docs["catalog"], docs["kb"])
    errors = _validate_kb_docs(docs["kb"], docs["catalog"])
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})

    now = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    catalog_path = Path(settings.catalog_path)
    kb_path = Path(settings.kb_path)
    catalog_backup = catalog_path.with_suffix(catalog_path.suffix + f".bak.{now}")
    kb_backup = kb_path.with_suffix(kb_path.suffix + f".bak.{now}")
    catalog_backup.write_text(catalog_path.read_text())
    kb_backup.write_text(kb_path.read_text())
    catalog_path.write_text(yamls["catalog"])
    kb_path.write_text(yamls["kb"])

    return {
        "ok": True,
        "catalog_path": settings.catalog_path,
        "kb_path": settings.kb_path,
        "backup_paths": {
            "catalog": str(catalog_backup),
            "kb": str(kb_backup),
        },
        "resolved_bindings": _resolved_bindings(payload.model),
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }


class ActionRequest(BaseModel):
    incident_id: str
    name: str
    payload: Dict[str, Any] = Field(default_factory=dict)


@app.post("/actions/dry-run")
def action_dry_run(payload: ActionRequest):
    if not persistence_enabled():
        raise HTTPException(status_code=503, detail="Persistence disabled. Set ENABLE_PERSISTENCE and DATABASE_URL.")
    execution_id = create_action_execution(payload.incident_id, payload.name, payload.payload, status="dry_run")
    record_audit("action.dry_run", incident_id=payload.incident_id, detail={"execution_id": execution_id})
    return {"id": execution_id, "status": "dry_run"}


@app.post("/actions/approve")
def action_approve(payload: ActionRequest):
    if not persistence_enabled():
        raise HTTPException(status_code=503, detail="Persistence disabled. Set ENABLE_PERSISTENCE and DATABASE_URL.")
    execution_id = create_action_execution(payload.incident_id, payload.name, payload.payload, status="approved")
    record_audit("action.approved", incident_id=payload.incident_id, detail={"execution_id": execution_id})
    return {"id": execution_id, "status": "approved"}


@app.post("/actions/execute")
def action_execute(payload: ActionRequest):
    if not persistence_enabled():
        raise HTTPException(status_code=503, detail="Persistence disabled. Set ENABLE_PERSISTENCE and DATABASE_URL.")
    execution_id = create_action_execution(payload.incident_id, payload.name, payload.payload, status="executing")
    record_audit("action.execute", incident_id=payload.incident_id, detail={"execution_id": execution_id})
    if not settings.live_mode:
        update_action_status(execution_id, "completed", {"result": "simulated"})
        record_audit("action.complete", incident_id=payload.incident_id, detail={"execution_id": execution_id})
        return {"id": execution_id, "status": "completed", "mode": "simulated"}
    record_audit("action.execute.requested", incident_id=payload.incident_id, detail={"execution_id": execution_id})
    return {"id": execution_id, "status": "executing", "mode": "live"}


@app.get("/actions/{execution_id}/status")
def action_status(execution_id: str):
    if not persistence_enabled():
        raise HTTPException(status_code=503, detail="Persistence disabled. Set ENABLE_PERSISTENCE and DATABASE_URL.")
    with get_db() as db:
        row = db.get(ActionExecution, execution_id)
        if not row:
            raise HTTPException(status_code=404, detail="Action execution not found")
        return {"id": row.id, "incident_id": row.incident_id, "status": row.status, "payload": row.payload}


@app.get("/audit")
def audit_events(limit: int = Query(50, ge=1, le=200)):
    if not persistence_enabled():
        return []
    with get_db() as db:
        rows = (
            db.execute(select(AuditEvent).order_by(desc(AuditEvent.created_at)).limit(limit))
            .scalars()
            .all()
        )
        return [
            {
                "id": row.id,
                "incident_id": row.incident_id,
                "actor": row.actor,
                "action": row.action,
                "detail": row.detail,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]


@app.get("/incidents")
def query_incidents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    environment: Optional[str] = None,
    severity: Optional[str] = None,
    subject: Optional[str] = None,
    title: Optional[str] = None,
    starts_after: Optional[str] = None,
    ends_before: Optional[str] = None,
):
    if not persistence_enabled():
        raise HTTPException(status_code=503, detail="Persistence disabled. Set ENABLE_PERSISTENCE and DATABASE_URL.")
    with get_db() as db:
        base = select(Incident)
        if environment:
            base = base.where(Incident.environment == environment)
        if severity:
            base = base.where(Incident.severity == severity)
        if subject:
            base = base.where(Incident.subject == subject)
        if title:
            base = base.where(Incident.title.ilike(f"%{title}%"))
        if starts_after:
            base = base.where(Incident.starts_at >= _parse_rfc3339(starts_after))
        if ends_before:
            base = base.where(Incident.ends_at <= _parse_rfc3339(ends_before))

        total = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
        rows = (
            db.execute(
                base.order_by(desc(Incident.created_at))
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .scalars()
            .all()
        )
        items = [
            {
                "id": row.id,
                "title": row.title,
                "severity": row.severity,
                "environment": row.environment,
                "subject": row.subject,
                "starts_at": row.starts_at.isoformat(),
                "ends_at": row.ends_at.isoformat(),
                "created_at": row.created_at.isoformat(),
                "updated_at": row.updated_at.isoformat(),
            }
            for row in rows
        ]
        return {"items": items, "page": page, "page_size": page_size, "total": total}


@app.get("/incidents/{incident_id}")
def get_incident(incident_id: str):
    if not persistence_enabled():
        raise HTTPException(status_code=503, detail="Persistence disabled. Set ENABLE_PERSISTENCE and DATABASE_URL.")
    with get_db() as db:
        row = db.get(Incident, incident_id)
        if not row:
            raise HTTPException(status_code=404, detail="Incident not found")
        latest_report = (
            db.execute(
                select(IncidentReport)
                .where(IncidentReport.incident_id == incident_id)
                .order_by(desc(IncidentReport.created_at))
                .limit(1)
            )
            .scalars()
            .first()
        )
        return {
            "id": row.id,
            "title": row.title,
            "severity": row.severity,
            "environment": row.environment,
            "subject": row.subject,
            "starts_at": row.starts_at.isoformat(),
            "ends_at": row.ends_at.isoformat(),
            "labels": row.labels,
            "annotations": row.annotations,
            "created_at": row.created_at.isoformat(),
            "updated_at": row.updated_at.isoformat(),
            "latest_report_id": latest_report.id if latest_report else None,
        }


@app.get("/incidents/{incident_id}/reports")
def list_reports(
    incident_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    if not persistence_enabled():
        raise HTTPException(status_code=503, detail="Persistence disabled. Set ENABLE_PERSISTENCE and DATABASE_URL.")
    with get_db() as db:
        row = db.get(Incident, incident_id)
        if not row:
            raise HTTPException(status_code=404, detail="Incident not found")
        base = select(IncidentReport).where(IncidentReport.incident_id == incident_id)
        total = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
        rows = (
            db.execute(
                base.order_by(desc(IncidentReport.created_at))
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            .scalars()
            .all()
        )
        items = [
            {
                "id": report.id,
                "incident_id": report.incident_id,
                "incident_summary": report.incident_summary,
                "created_at": report.created_at.isoformat(),
            }
            for report in rows
        ]
        return {"items": items, "page": page, "page_size": page_size, "total": total}


@app.get("/incidents/{incident_id}/reports/latest")
def latest_report(incident_id: str):
    if not persistence_enabled():
        raise HTTPException(status_code=503, detail="Persistence disabled. Set ENABLE_PERSISTENCE and DATABASE_URL.")
    with get_db() as db:
        report = (
            db.execute(
                select(IncidentReport)
                .where(IncidentReport.incident_id == incident_id)
                .order_by(desc(IncidentReport.created_at))
                .limit(1)
            )
            .scalars()
            .first()
        )
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        return {
            "id": report.id,
            "incident_id": report.incident_id,
            "incident_summary": report.incident_summary,
            "created_at": report.created_at.isoformat(),
            "report": report.report,
        }


@app.get("/reports/{report_id}")
def get_report(report_id: str):
    if not persistence_enabled():
        raise HTTPException(status_code=503, detail="Persistence disabled. Set ENABLE_PERSISTENCE and DATABASE_URL.")
    with get_db() as db:
        report = db.get(IncidentReport, report_id)
        if not report:
            raise HTTPException(status_code=404, detail="Report not found")
        return {
            "id": report.id,
            "incident_id": report.incident_id,
            "incident_summary": report.incident_summary,
            "created_at": report.created_at.isoformat(),
            "report": report.report,
        }
