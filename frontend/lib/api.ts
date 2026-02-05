const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

export interface Incident {
  id: string;
  title: string;
  severity: string;
  environment: string;
  subject?: string;
  status?: string;
  updated?: string;
  starts_at?: string;
  ends_at?: string;
  created_at?: string;
  updated_at?: string;
  latest_report_id?: string;
  time_range?: { start: string; end: string };
}

export interface TimelineItem {
  time: string;
  label: string;
  source: string;
  kind?: string;
}

export interface Hypothesis {
  id: string;
  statement: string;
  confidence: number;
  evidence_ids?: string[];
  validations?: string[];
  score_breakdown?: Record<string, number>;
  supporting_evidence_ids?: string[];
  contradictions?: string[];
}

export interface Action {
  id: string;
  name: string;
  risk: string;
  requires_approval: boolean;
  intent?: string;
}

export interface EvidenceItem {
  id: string;
  kind: string;
  source: string;
  summary: string;
  time_range: { start: string; end: string };
  samples?: string[];
  top_signals?: Record<string, unknown>;
  pointers?: Array<{ title?: string; url?: string }>;
  tags?: string[];
}

export interface RCAReport {
  id?: string;
  incident_id?: string;
  incident_summary: string;
  time_range: { start: string; end: string };
  top_hypothesis: Hypothesis;
  other_hypotheses: Hypothesis[];
  fallback_hypotheses?: Hypothesis[];
  evidence: EvidenceItem[];
  supporting_evidence?: string[];
  what_changed?: Record<string, unknown>;
  impact_scope?: Record<string, unknown>;
  next_validations: string[];
  created_at?: string;
}

export interface Runbook {
  subject: string;
  name: string;
  indicators: string[];
}

export interface Pattern {
  subject: string;
  pattern: string;
  indicators: string[];
}

async function fetchJSON<T>(url: string): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`);
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }
  return res.json();
}

export async function getMode(): Promise<{ live_mode: boolean }> {
  return fetchJSON("/ui/mode");
}

export async function getIncidents(): Promise<Incident[]> {
  return fetchJSON("/ui/incidents");
}

export async function getIncident(id: string): Promise<Incident> {
  return fetchJSON(`/incidents/${id}`);
}

export async function getIncidentTimeline(id: string): Promise<TimelineItem[]> {
  return fetchJSON(`/ui/incidents/${id}/timeline`);
}

export async function getIncidentHypotheses(id: string): Promise<Hypothesis[]> {
  return fetchJSON(`/ui/incidents/${id}/hypotheses`);
}

export async function getActions(): Promise<Action[]> {
  return fetchJSON("/ui/actions");
}

export async function getSummary(): Promise<{
  summary: string;
  confidence: number | null;
  citations: string[];
}> {
  return fetchJSON("/ui/summary");
}

export async function getAttentionQueue(
  limit = 5
): Promise<
  Array<{
    id: string;
    title: string;
    severity: string;
    environment: string;
    updated_at: string;
  }>
> {
  return fetchJSON(`/ui/attention?limit=${limit}`);
}

export async function getSignalsTimeline(
  incidentId?: string
): Promise<TimelineItem[]> {
  const url = incidentId
    ? `/signals/timeline?incident_id=${incidentId}`
    : "/signals/timeline";
  return fetchJSON(url);
}

export async function getSignalsCorrelation(incidentId?: string): Promise<{
  pairs: Array<{ pair: string; score: number }>;
}> {
  const url = incidentId
    ? `/signals/correlation?incident_id=${incidentId}`
    : "/signals/correlation";
  return fetchJSON(url);
}

export async function getIncidentChanges(
  id: string
): Promise<EvidenceItem[]> {
  return fetchJSON(`/incidents/${id}/changes`);
}

export async function getIncidentAlerts(
  id: string
): Promise<EvidenceItem[]> {
  return fetchJSON(`/incidents/${id}/alerts`);
}

export async function getRunbooks(): Promise<Runbook[]> {
  return fetchJSON("/knowledge/runbooks");
}

export async function getPatterns(): Promise<Pattern[]> {
  return fetchJSON("/knowledge/patterns");
}

export async function getHistoricalIncidents(
  limit = 20
): Promise<Incident[]> {
  return fetchJSON(`/knowledge/incidents?limit=${limit}`);
}

export async function getOnboardingConfig(): Promise<{
  subjects: unknown[];
  providers: Array<{
    id: string;
    category: string;
    type: string;
    capabilities: Record<string, unknown>;
    config: Record<string, unknown>;
  }>;
  catalog_path: string;
  kb_path: string;
}> {
  return fetchJSON("/knowledge/onboarding");
}

export async function queryIncidents(params: {
  page?: number;
  page_size?: number;
  environment?: string;
  severity?: string;
  subject?: string;
  title?: string;
}): Promise<{
  items: Incident[];
  page: number;
  page_size: number;
  total: number;
}> {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set("page", String(params.page));
  if (params.page_size) searchParams.set("page_size", String(params.page_size));
  if (params.environment) searchParams.set("environment", params.environment);
  if (params.severity) searchParams.set("severity", params.severity);
  if (params.subject) searchParams.set("subject", params.subject);
  if (params.title) searchParams.set("title", params.title);
  return fetchJSON(`/incidents?${searchParams.toString()}`);
}

export async function getLatestReport(
  incidentId: string
): Promise<RCAReport & { id: string; incident_id: string; created_at: string }> {
  return fetchJSON(`/incidents/${incidentId}/reports/latest`);
}

export async function getReport(
  reportId: string
): Promise<{ id: string; incident_id: string; report: RCAReport; created_at: string }> {
  return fetchJSON(`/reports/${reportId}`);
}

export async function triggerInvestigation(payload: {
  title: string;
  severity: string;
  environment: string;
  subject: string;
  starts_at?: string;
  ends_at?: string;
}): Promise<RCAReport> {
  const res = await fetch(`${API_BASE}/webhook/incident`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }
  return res.json();
}
