export type HealthResponse = { ok: boolean };

export type IncidentRequest = {
  title: string;
  severity: string;
  environment: string;
  subject: string;
  starts_at?: string | null;
  ends_at?: string | null;
  labels?: Record<string, string>;
  annotations?: Record<string, string>;
  raw?: Record<string, unknown>;
};

export type IncidentListItem = {
  id: string;
  title: string;
  severity: string;
  environment: string;
  subject: string;
  starts_at: string;
  ends_at: string;
  created_at: string;
  updated_at: string;
};

export type IncidentListResponse = {
  items: IncidentListItem[];
  page: number;
  page_size: number;
  total: number;
};

export type RCAReportResponse = {
  id: string;
  incident_id: string;
  incident_summary: string;
  created_at: string;
  report: {
    time_range?: { start: string; end: string };
    evidence?: Array<{
      id: string;
      kind: string;
      source: string;
      time_range: { start: string; end: string };
      summary: string;
    }>;
    top_hypothesis?: {
      id: string;
      statement: string;
      confidence: number;
      supporting_evidence_ids: string[];
      validations: string[];
    };
    other_hypotheses?: Array<{
      id: string;
      statement: string;
      confidence: number;
      supporting_evidence_ids: string[];
      validations: string[];
    }>;
    next_validations?: string[];
  };
};

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch('/api/health');
  if (!res.ok) {
    throw new Error(`Health check failed (${res.status})`);
  }
  return res.json();
}

export async function fetchIncidents(params?: {
  page?: number;
  page_size?: number;
  environment?: string;
  severity?: string;
  subject?: string;
  title?: string;
}): Promise<IncidentListResponse> {
  const search = new URLSearchParams();
  if (params?.page) search.set('page', String(params.page));
  if (params?.page_size) search.set('page_size', String(params.page_size));
  if (params?.environment) search.set('environment', params.environment);
  if (params?.severity) search.set('severity', params.severity);
  if (params?.subject) search.set('subject', params.subject);
  if (params?.title) search.set('title', params.title);

  const res = await fetch(`/api/incidents?${search.toString()}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Incidents query failed (${res.status}): ${text}`);
  }
  return res.json();
}

export async function fetchIncident(incidentId: string): Promise<{
  id: string;
  title: string;
  severity: string;
  environment: string;
  subject: string;
  starts_at: string;
  ends_at: string;
  labels?: Record<string, string>;
  annotations?: Record<string, string>;
  created_at: string;
  updated_at: string;
  latest_report_id?: string | null;
}> {
  const res = await fetch(`/api/incidents/${incidentId}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Incident fetch failed (${res.status}): ${text}`);
  }
  return res.json();
}

export async function fetchLatestReport(incidentId: string): Promise<RCAReportResponse> {
  const res = await fetch(`/api/incidents/${incidentId}/reports/latest`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Latest report failed (${res.status}): ${text}`);
  }
  return res.json();
}

export async function fetchSummary(): Promise<{ summary: string; confidence: number | null; citations: string[] }> {
  const res = await fetch('/api/ui/summary');
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Summary failed (${res.status}): ${text}`);
  }
  return res.json();
}

export async function fetchUiMode(): Promise<{ live_mode: boolean }> {
  const res = await fetch('/api/ui/mode');
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Mode failed (${res.status}): ${text}`);
  }
  return res.json();
}

export async function fetchAttention(limit = 5): Promise<Array<{ id: string; title: string; severity: string; environment: string; updated_at: string }>> {
  const res = await fetch(`/api/ui/attention?limit=${limit}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Attention failed (${res.status}): ${text}`);
  }
  return res.json();
}

export async function fetchSignalsTimeline(incidentId?: string): Promise<Array<{ time: string; label: string; source: string; kind: string }>> {
  const query = incidentId ? `?incident_id=${incidentId}` : '';
  const res = await fetch(`/api/signals/timeline${query}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Signals timeline failed (${res.status}): ${text}`);
  }
  return res.json();
}

export async function fetchSignalsCorrelation(incidentId?: string): Promise<{ pairs: Array<{ pair: string; score: number }> }> {
  const query = incidentId ? `?incident_id=${incidentId}` : '';
  const res = await fetch(`/api/signals/correlation${query}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Signals correlation failed (${res.status}): ${text}`);
  }
  return res.json();
}

export async function fetchIncidentChanges(incidentId: string): Promise<Array<Record<string, unknown>>> {
  const res = await fetch(`/api/incidents/${incidentId}/changes`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Incident changes failed (${res.status}): ${text}`);
  }
  return res.json();
}

export async function fetchIncidentAlerts(incidentId: string): Promise<Array<Record<string, unknown>>> {
  const res = await fetch(`/api/incidents/${incidentId}/alerts`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Incident alerts failed (${res.status}): ${text}`);
  }
  return res.json();
}

export async function fetchRunbooks(): Promise<Array<{ subject: string; name: string; indicators: string[] }>> {
  const res = await fetch('/api/knowledge/runbooks');
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Runbooks failed (${res.status}): ${text}`);
  }
  return res.json();
}

export async function fetchPatterns(): Promise<Array<{ subject: string; pattern: string; indicators: string[] }>> {
  const res = await fetch('/api/knowledge/patterns');
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Patterns failed (${res.status}): ${text}`);
  }
  return res.json();
}

export type OnboardingResponse = {
  subjects: Array<Record<string, unknown>>;
  providers: Array<{
    id: string;
    category?: string;
    type?: string;
    capabilities?: Record<string, unknown>;
    config?: Record<string, unknown>;
  }>;
  catalog_path: string;
  kb_path: string;
};

export async function fetchOnboarding(): Promise<OnboardingResponse> {
  const res = await fetch('/api/knowledge/onboarding');
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Onboarding failed (${res.status}): ${text}`);
  }
  return res.json();
}

export async function postAction(action: { incident_id: string; name: string; payload?: Record<string, unknown> }, endpoint: 'dry-run' | 'approve' | 'execute') {
  const res = await fetch(`/api/actions/${endpoint}`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(action)
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Action ${endpoint} failed (${res.status}): ${text}`);
  }
  return res.json();
}

export async function postIncident(payload: IncidentRequest): Promise<unknown> {
  const res = await fetch('/api/webhook/incident', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Incident webhook failed (${res.status}): ${text}`);
  }
  return res.json();
}
