from __future__ import annotations

from typing import Optional

from core.config import settings
from core.db import get_db, init_db
from datetime import datetime, timezone
from core.models import IncidentInput, RCAReport
from core.persistence_models import Action, ActionExecution, AuditEvent, EvidenceItem, Hypothesis, Incident, IncidentReport


def persistence_enabled() -> bool:
    return bool(settings.enable_persistence and settings.database_url)

def _parse_rfc3339(ts: str) -> datetime:
    if not ts:
        return datetime.now(timezone.utc)
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def bootstrap() -> None:
    if not persistence_enabled():
        return
    init_db()


def save_report(incident: IncidentInput, report: RCAReport) -> Optional[str]:
    if not persistence_enabled():
        return None

    with get_db() as db:
        incident_row = Incident(
            title=incident.title,
            severity=incident.severity,
            environment=incident.environment,
            subject=incident.subject,
            starts_at=_parse_rfc3339(incident.time_range.start),
            ends_at=_parse_rfc3339(incident.time_range.end),
            labels=incident.labels,
            annotations=incident.annotations,
            raw=incident.raw,
        )
        db.add(incident_row)
        db.flush()

        report_row = IncidentReport(
            incident_id=incident_row.id,
            incident_summary=report.incident_summary,
            report=report.model_dump(),
        )
        db.add(report_row)

        for ev in report.evidence:
            db.add(
                EvidenceItem(
                    id=ev.id,
                    incident_id=incident_row.id,
                    kind=ev.kind,
                    source=ev.source,
                    time_start=_parse_rfc3339(ev.time_range.start),
                    time_end=_parse_rfc3339(ev.time_range.end),
                    query=ev.query,
                    summary=ev.summary,
                    samples=ev.samples,
                    top_signals=ev.top_signals,
                    pointers=ev.pointers,
                    tags=ev.tags,
                )
            )

        all_hypotheses = [report.top_hypothesis, *report.other_hypotheses]
        for hyp in all_hypotheses:
            db.add(
                Hypothesis(
                    id=hyp.id,
                    incident_id=incident_row.id,
                    statement=hyp.statement,
                    confidence=hyp.confidence,
                    score_breakdown=hyp.score_breakdown,
                    supporting_evidence_ids=hyp.supporting_evidence_ids,
                    contradictions=hyp.contradictions,
                    validations=hyp.validations,
                    is_top=hyp.id == report.top_hypothesis.id,
                )
            )

        for validation in report.next_validations:
            db.add(
                Action(
                    incident_id=incident_row.id,
                    name=validation,
                    risk="Low",
                    requires_approval=True,
                    intent="validation",
                    payload={},
                )
            )

        return incident_row.id


def create_action_execution(incident_id: str, name: str, payload: dict, status: str = "pending") -> str:
    if not persistence_enabled():
        raise RuntimeError("Persistence disabled")
    with get_db() as db:
        row = ActionExecution(
            incident_id=incident_id,
            name=name,
            status=status,
            payload=payload,
        )
        db.add(row)
        db.flush()
        return row.id


def update_action_status(execution_id: str, status: str, detail: dict | None = None) -> None:
    if not persistence_enabled():
        raise RuntimeError("Persistence disabled")
    with get_db() as db:
        row = db.get(ActionExecution, execution_id)
        if not row:
            raise ValueError("Execution not found")
        row.status = status
        row.payload = {**(row.payload or {}), **(detail or {})}


def record_audit(action: str, actor: str = "system", incident_id: str | None = None, detail: dict | None = None) -> None:
    if not persistence_enabled():
        return
    with get_db() as db:
        db.add(
            AuditEvent(
                incident_id=incident_id,
                actor=actor,
                action=action,
                detail=detail or {},
            )
        )
