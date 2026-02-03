from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field, field_validator

from core.models import IncidentInput, TimeRange
from core.orchestrator import run, run_incident, _now_rfc3339, _shift_rfc3339

app = FastAPI(title="RCA Investigation Agent")

@app.get("/health")
def health():
    return {"ok": True}

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
    incident = IncidentInput(
        title=payload.title,
        severity=payload.severity,
        environment=payload.environment,
        subject=payload.subject,
        time_range=tr,
        labels=payload.labels,
        annotations=payload.annotations,
        raw=payload.raw,
    )
    return run_incident(incident)
