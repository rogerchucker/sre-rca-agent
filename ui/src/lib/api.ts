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

export type OnboardingYamlResponse = {
  catalog_yaml: string;
  kb_yaml: string;
  catalog_path: string;
  kb_path: string;
};

export type OnboardingProviderModel = {
  id: string;
  category: string;
  type: string;
  operations: string[];
  config: Record<string, unknown>;
};

export type OnboardingFailureModeModel = {
  name: string;
  indicators: string[];
};

export type OnboardingSubjectModel = {
  name: string;
  environment: string;
  aliases: string[];
  bindings: Record<string, string>;
  dependencies: string[];
  runbooks: string[];
  known_failure_modes: OnboardingFailureModeModel[];
  deploy_context: Record<string, unknown>;
  vcs_context: Record<string, unknown>;
  log_evidence: Record<string, unknown>;
};

export type OnboardingModel = {
  providers: OnboardingProviderModel[];
  subjects: OnboardingSubjectModel[];
};

export type OnboardingProfile = 'template' | 'demo';

export type BindingResolution = {
  capability: string;
  provider_id: string;
  resolved: boolean;
  provider_category: string | null;
  provider_type: string | null;
};

export type ResolvedSubjectBindings = {
  subject: string;
  environment: string;
  bindings: BindingResolution[];
};

export type OnboardingPreviewResponse = {
  ok: boolean;
  errors: string[];
  diffs: {
    catalog: string;
    kb: string;
  };
  resolved_bindings?: ResolvedSubjectBindings[];
  model?: OnboardingModel;
};

export async function fetchOnboardingRaw(): Promise<OnboardingYamlResponse> {
  const res = await fetch('/api/knowledge/onboarding/raw');
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Onboarding raw failed (${res.status}): ${text}`);
  }
  return res.json();
}

export async function previewOnboardingYaml(payload: { catalog_yaml: string; kb_yaml: string }): Promise<OnboardingPreviewResponse> {
  const res = await fetch('/api/knowledge/onboarding/preview', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Onboarding preview failed (${res.status}): ${text}`);
  }
  return res.json();
}

export async function fetchOnboardingModel(): Promise<{
  model: OnboardingModel;
  resolved_bindings: ResolvedSubjectBindings[];
  available_binding_capabilities: string[];
  profile: OnboardingProfile;
  source_catalog_path: string;
  source_kb_path: string;
  catalog_path: string;
  kb_path: string;
}> {
  const res = await fetch('/api/knowledge/onboarding/model');
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Onboarding model failed (${res.status}): ${text}`);
  }
  return res.json();
}

export async function fetchOnboardingModelByProfile(profile: OnboardingProfile): Promise<{
  model: OnboardingModel;
  resolved_bindings: ResolvedSubjectBindings[];
  available_binding_capabilities: string[];
  profile: OnboardingProfile;
  source_catalog_path: string;
  source_kb_path: string;
  catalog_path: string;
  kb_path: string;
}> {
  const res = await fetch(`/api/knowledge/onboarding/model?profile=${profile}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Onboarding model failed (${res.status}): ${text}`);
  }
  return res.json();
}

export async function previewOnboardingModel(payload: { model: OnboardingModel }): Promise<{
  ok: boolean;
  errors: string[];
  yaml: { catalog_yaml: string; kb_yaml: string };
  diffs: { catalog: string; kb: string };
  resolved_bindings: ResolvedSubjectBindings[];
}> {
  const res = await fetch('/api/knowledge/onboarding/model/preview', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Onboarding model preview failed (${res.status}): ${text}`);
  }
  return res.json();
}

export async function applyOnboardingYaml(payload: { catalog_yaml: string; kb_yaml: string }): Promise<{
  ok: boolean;
  catalog_path: string;
  kb_path: string;
  backup_paths: { catalog: string; kb: string };
  updated_at: string;
}> {
  const res = await fetch('/api/knowledge/onboarding/apply', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Onboarding apply failed (${res.status}): ${text}`);
  }
  return res.json();
}

export async function applyOnboardingModel(payload: { model: OnboardingModel }): Promise<{
  ok: boolean;
  catalog_path: string;
  kb_path: string;
  backup_paths: { catalog: string; kb: string };
  resolved_bindings: ResolvedSubjectBindings[];
  updated_at: string;
}> {
  const res = await fetch('/api/knowledge/onboarding/model/apply', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Onboarding model apply failed (${res.status}): ${text}`);
  }
  return res.json();
}

export type OnboardingAgentOp = {
  type: 'add_provider' | 'add_subject' | 'bind_subject_provider';
  provider?: Record<string, unknown>;
  subject?: Record<string, unknown>;
  binding?: {
    subject: string;
    capability: string;
    provider_id: string;
  };
};

export async function planOnboardingChanges(payload: {
  intent: string;
  model: OnboardingModel;
  policy?: Record<string, unknown>;
}): Promise<{
  proposed_ops: OnboardingAgentOp[];
  preview_model: OnboardingModel;
  warnings: string[];
  requires_confirmation: boolean;
  applied_ops: OnboardingAgentOp[];
  rejected_ops: OnboardingAgentOp[];
  resolved_bindings: ResolvedSubjectBindings[];
}> {
  const res = await fetch('/api/knowledge/onboarding/agent/plan', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Onboarding agent plan failed (${res.status}): ${text}`);
  }
  return res.json();
}

export async function applyOnboardingOps(payload: {
  model: OnboardingModel;
  ops: OnboardingAgentOp[];
  policy?: Record<string, unknown>;
}): Promise<{
  model: OnboardingModel;
  warnings: string[];
  applied_ops: OnboardingAgentOp[];
  rejected_ops: OnboardingAgentOp[];
  resolved_bindings: ResolvedSubjectBindings[];
}> {
  const res = await fetch('/api/knowledge/onboarding/agent/apply-ops', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Onboarding agent apply failed (${res.status}): ${text}`);
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
