from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
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
from api.copilotkit_agent import add_copilotkit_endpoint

app = FastAPI(
    title="RCA Investigation Agent",
    description="""
AI-powered Root Cause Analysis for Incident Investigation.

## Features

- **Incident Investigation**: Analyze incidents using evidence from logs, deployments, and code changes
- **Hypothesis Generation**: Generate and rank root cause hypotheses with confidence scores
- **Knowledge Base**: Leverage organizational knowledge for context-aware analysis
- **CopilotKit Integration**: Conversational AI interface for interactive investigations

## Authentication

This API does not require authentication by default. For production deployments,
implement appropriate authentication middleware.
    """,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)

# CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CopilotKit/AG-UI endpoint for RCA agent
add_copilotkit_endpoint(app)
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
