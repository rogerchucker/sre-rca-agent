from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

EvidenceKind = Literal["alert", "logs", "metrics", "deploy", "change", "trace", "event", "build", "other"]

class TimeRange(BaseModel):
    start: str  # RFC3339
    end: str    # RFC3339

class IncidentInput(BaseModel):
    title: str
    severity: str
    environment: str
    subject: str  # application/service/component identifier (string)
    time_range: TimeRange
    labels: Dict[str, str] = Field(default_factory=dict)
    annotations: Dict[str, str] = Field(default_factory=dict)
    raw: Dict[str, Any] = Field(default_factory=dict)

class EvidenceItem(BaseModel):
    id: str
    kind: EvidenceKind
    source: str              # provider instance id (from KB)
    time_range: TimeRange
    query: str               # provider-native query or request description
    summary: str
    samples: List[str] = Field(default_factory=list)
    top_signals: Dict[str, Any] = Field(default_factory=dict)
    pointers: List[Dict[str, str]] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

class Hypothesis(BaseModel):
    id: str
    statement: str
    confidence: float
    score_breakdown: Dict[str, float]
    supporting_evidence_ids: List[str]
    contradictions: List[str] = Field(default_factory=list)
    validations: List[str] = Field(default_factory=list)

class RCAReport(BaseModel):
    incident_summary: str
    time_range: TimeRange
    top_hypothesis: Hypothesis
    other_hypotheses: List[Hypothesis]
    evidence: List[EvidenceItem]
    next_validations: List[str]

# ---- Provider-neutral request objects ----

class LogQueryRequest(BaseModel):
    subject: str
    environment: str
    time_range: TimeRange
    intent: Literal["signature_counts", "samples"]
    stream_selectors: Dict[str, str] = Field(default_factory=dict)
    parse: Dict[str, Any] = Field(default_factory=dict)       # e.g., {"format":"json","fields":{...}}
    filters: Dict[str, Any] = Field(default_factory=dict)     # e.g., {"status": 500}
    limit: int = 200

class DeployQueryRequest(BaseModel):
    subject: str
    environment: str
    time_range: TimeRange
    limit: int = 20

class ChangeQueryRequest(BaseModel):
    subject: str
    environment: str
    time_range: TimeRange
    include_prs: bool = True
    include_commits: bool = False
    limit: int = 30

class BuildQueryRequest(BaseModel):
    subject: str
    environment: str
    time_range: TimeRange
    limit: int = 30

class MetricsQueryRequest(BaseModel):
    subject: str
    environment: str
    time_range: TimeRange
    query: str
    step_seconds: int = 60
    limit: int = 50

class TraceQueryRequest(BaseModel):
    subject: str
    environment: str
    time_range: TimeRange
    service_name: Optional[str] = None
    limit: int = 20

class EventQueryRequest(BaseModel):
    subject: str
    environment: str
    time_range: TimeRange
    namespace: Optional[str] = None
    selector: Optional[str] = None
    limit: int = 200

class K8sLogQueryRequest(BaseModel):
    subject: str
    environment: str
    time_range: TimeRange
    namespace: Optional[str] = None
    selector: Optional[str] = None
    container: Optional[str] = None
    limit: int = 200

# ---- Core execution state ----

class AgentState(BaseModel):
    incident: IncidentInput
    kb_slice: Dict[str, Any] = Field(default_factory=dict)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    hypotheses: List[Hypothesis] = Field(default_factory=list)
    plan: List[Dict[str, Any]] = Field(default_factory=list)
    iteration: int = 0
    report: Optional[RCAReport] = None
