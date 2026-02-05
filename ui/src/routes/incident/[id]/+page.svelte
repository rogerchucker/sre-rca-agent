<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import {
    fetchIncident,
    fetchIncidentAlerts,
    fetchIncidentChanges,
    fetchIncidents,
    fetchLatestReport,
    fetchPatterns,
    fetchRunbooks,
    type RCAReportResponse
  } from '$lib/api';
  import { incidentTabs } from '$lib/stores/incident-tabs';

  let incident: Awaited<ReturnType<typeof fetchIncident>> | null = null;
  let report: RCAReportResponse | null = null;
  let error = '';
  let changes: Array<Record<string, unknown>> = [];
  let alerts: Array<Record<string, unknown>> = [];
  let runbooks: Array<{ subject: string; name: string; indicators: string[] }> = [];
  let patterns: Array<{ subject: string; pattern: string; indicators: string[] }> = [];
  let related: Array<{ id: string; title: string; severity: string; environment: string }> = [];

  const steps = ['Idle', 'Collecting Evidence', 'Hypothesizing', 'Recommendation Ready'];

  function parseTime(value?: string | null) {
    if (!value) return null;
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? null : d;
  }

  function isActive() {
    const end = parseTime(incident?.ends_at);
    if (!end) return true;
    return end.getTime() > Date.now();
  }

  function elapsed() {
    const start = parseTime(incident?.starts_at);
    if (!start) return '—';
    const end = isActive() ? new Date() : parseTime(incident?.ends_at) ?? new Date();
    const delta = end.getTime() - start.getTime();
    const minutes = Math.round(delta / 60000);
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.round(minutes / 60);
    if (hours < 24) return `${hours}h`;
    const days = Math.round(hours / 24);
    return `${days}d`;
  }

  function currentStepIndex() {
    if (!report?.report) return 0;
    const evidence = report.report.evidence ?? [];
    const hasEvidence = evidence.length > 0;
    const hasHypothesis = !!report.report.top_hypothesis;
    if (hasHypothesis) return 3;
    if (hasEvidence) return 2;
    return 1;
  }

  function kbApplied() {
    if (!incident) return { runbooks: [], patterns: [] };
    return {
      runbooks: runbooks.filter((rb) => rb.subject === incident.subject),
      patterns: patterns.filter((pt) => pt.subject === incident.subject)
    };
  }

  onMount(async () => {
    const id = $page.params.id;
    if (!id) {
      error = 'Incident id missing.';
      return;
    }
    try {
      incident = await fetchIncident(id);
      incidentTabs.openTab({
        id: incident.id,
        title: incident.title,
        severity: incident.severity,
        environment: incident.environment,
        subject: incident.subject
      });
      report = await fetchLatestReport(id);
      changes = await fetchIncidentChanges(id);
      alerts = await fetchIncidentAlerts(id);
      runbooks = await fetchRunbooks();
      patterns = await fetchPatterns();
      const relatedResp = await fetchIncidents({
        page: 1,
        page_size: 4,
        subject: incident.subject,
        environment: incident.environment
      });
      related = relatedResp.items
        .filter((item) => item.id !== incident?.id)
        .slice(0, 3)
        .map((item) => ({
          id: item.id,
          title: item.title,
          severity: item.severity,
          environment: item.environment
        }));
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load incident details.';
    }
  });
</script>

{#if error}
  <section class="surface p-6">
    <div class="text-xs text-danger-500">{error}</div>
  </section>
{:else if !incident}
  <section class="surface p-6">
    <div class="text-sm text-mist-300">Loading incident…</div>
  </section>
{:else}
  <section class="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
    <div class="surface p-6">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Incident details</div>
          <div class="mt-2 text-2xl font-semibold">{incident.title}</div>
          <div class="mt-2 flex flex-wrap gap-2 text-xs text-mist-300">
            <span class="chip">{incident.severity}</span>
            <span class="chip">{incident.environment}</span>
            <span class="chip">{incident.subject}</span>
          </div>
        </div>
        <div class="text-right text-xs text-mist-300">
          <div>Elapsed</div>
          <div class="text-lg font-semibold text-mist-100">{elapsed()}</div>
          <div class={`mt-2 badge ${isActive() ? 'text-accent-500' : 'text-mist-300'}`}>
            {isActive() ? 'Active' : 'Resolved'}
          </div>
        </div>
      </div>

      <div class="mt-6 grid gap-4 sm:grid-cols-2">
        <div class="surface-subtle card-contrast p-4">
          <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Alert context</div>
          <div class="mt-3 text-sm text-mist-200">
            <div>Started: {incident.starts_at}</div>
            <div>Ends: {incident.ends_at ?? '—'}</div>
          </div>
          <div class="mt-3 text-xs text-mist-300">Labels</div>
          <div class="mt-2 flex flex-wrap gap-2 text-xs">
            {#each Object.entries(incident.labels ?? {}) as [key, value]}
              <span class="chip">{key}: {value}</span>
            {/each}
            {#if Object.keys(incident.labels ?? {}).length === 0}
              <span class="text-mist-300">No labels</span>
            {/if}
          </div>
          <div class="mt-3 text-xs text-mist-300">Annotations</div>
          <div class="mt-2 flex flex-wrap gap-2 text-xs">
            {#each Object.entries(incident.annotations ?? {}) as [key, value]}
              <span class="chip">{key}: {value}</span>
            {/each}
            {#if Object.keys(incident.annotations ?? {}).length === 0}
              <span class="text-mist-300">No annotations</span>
            {/if}
          </div>
        </div>

        <div class="surface-subtle card-contrast p-4">
          <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Related incidents</div>
          <div class="mt-4 space-y-2 text-sm">
            {#if related.length === 0}
              <div class="text-mist-300">No related incidents.</div>
            {:else}
              {#each related as item}
                <div class="surface-subtle card-contrast p-3">
                  <div class="text-sm font-semibold">{item.title}</div>
                  <div class="mt-1 text-xs text-mist-300">{item.severity} · {item.environment}</div>
                </div>
              {/each}
            {/if}
          </div>
        </div>
      </div>
    </div>

    <div class="surface p-6">
      <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Investigation state</div>
      <div class="mt-2 text-xl font-semibold">Workflow progress</div>
      <div class="mt-5 stepper">
        {#each steps as step, index}
          <div class={`step ${index === currentStepIndex() ? 'step-active' : index < currentStepIndex() ? 'step-done' : ''}`}>
            <div class="step-dot"></div>
            <div class="step-label">{step}</div>
          </div>
        {/each}
      </div>

      <div class="mt-6">
        <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Related alerts</div>
        <div class="mt-3 space-y-3 text-sm text-mist-200">
          {#if alerts.length === 0}
            <div class="surface-subtle card-contrast p-3 text-sm text-mist-300">No alerts available.</div>
          {:else}
            {#each alerts as alert}
              <div class="surface-subtle card-contrast p-3">
                {alert.summary ?? alert.query ?? 'Alert item'}
              </div>
            {/each}
          {/if}
        </div>
      </div>
    </div>
  </section>

  <section class="mt-6 grid gap-6 lg:grid-cols-[1.2fr_1fr]">
    <div class="surface p-6">
      <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Evidence in use</div>
      <div class="mt-4 space-y-4">
        {#if report?.report?.evidence && report.report.evidence.length > 0}
          {#each report.report.evidence as item}
            <div class="surface-subtle card-contrast p-4">
              <div class="text-xs text-mist-300">{item.time_range.start} · {item.source}</div>
              <div class="mt-2 text-sm font-semibold">{item.summary}</div>
            </div>
          {/each}
        {:else}
          <div class="text-sm text-mist-300">No evidence available yet.</div>
        {/if}
      </div>

      <div class="mt-6">
        <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Relevant changes</div>
        <div class="mt-3 space-y-3 text-sm text-mist-200">
          {#if changes.length === 0}
            <div class="surface-subtle card-contrast p-3 text-sm text-mist-300">No related changes available.</div>
          {:else}
            {#each changes as change}
              <div class="surface-subtle card-contrast p-3">{change.summary ?? change.query ?? 'Change item'}</div>
            {/each}
          {/if}
        </div>
      </div>
    </div>

    <div class="surface p-6">
      <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Knowledge base applied</div>
      <div class="mt-4 space-y-4">
        <div>
          <div class="text-xs text-mist-300">Runbooks</div>
          <div class="mt-2 space-y-2 text-sm text-mist-200">
            {#if kbApplied().runbooks.length === 0}
              <div class="text-mist-300">No runbooks matched.</div>
            {:else}
              {#each kbApplied().runbooks as rb}
                <div class="surface-subtle card-contrast p-3">{rb.name}</div>
              {/each}
            {/if}
          </div>
        </div>
        <div>
          <div class="text-xs text-mist-300">Playbooks</div>
          <div class="mt-2 space-y-2 text-sm text-mist-200">
            {#if kbApplied().patterns.length === 0}
              <div class="text-mist-300">No playbooks matched.</div>
            {:else}
              {#each kbApplied().patterns as pt}
                <div class="surface-subtle card-contrast p-3">{pt.pattern}</div>
              {/each}
            {/if}
          </div>
        </div>
      </div>
    </div>
  </section>

  <section class="mt-6 grid gap-6 lg:grid-cols-2">
    <div class="surface p-6">
      <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Hypotheses</div>
      <div class="mt-4 space-y-4">
        {#if report?.report?.top_hypothesis}
          <div class="surface-subtle card-contrast p-4">
            <div class="flex items-center justify-between gap-2">
              <div class="text-sm font-semibold">{report.report.top_hypothesis.statement}</div>
              <div class="text-xs text-accent-500">{Math.round(report.report.top_hypothesis.confidence * 100)}%</div>
            </div>
          </div>
        {/if}
        {#if report?.report?.other_hypotheses}
          {#each report.report.other_hypotheses as hypothesis}
            <div class="surface-subtle card-contrast p-4">
              <div class="flex items-center justify-between gap-2">
                <div class="text-sm font-semibold">{hypothesis.statement}</div>
                <div class="text-xs text-accent-500">{Math.round(hypothesis.confidence * 100)}%</div>
              </div>
            </div>
          {/each}
        {/if}
        {#if !report?.report?.top_hypothesis && !report?.report?.other_hypotheses}
          <div class="text-sm text-mist-300">No hypotheses available.</div>
        {/if}
      </div>
    </div>

    <div class="surface p-6">
      <div class="text-xs uppercase tracking-[0.3em] text-mist-300">LLM recommendation</div>
      <div class="mt-2 text-xl font-semibold">Recommendation summary</div>
      <p class="mt-3 text-sm text-mist-200">
        {report?.incident_summary ?? 'Awaiting RCA output for reasoning details.'}
      </p>
      {#if report?.report?.top_hypothesis}
        <div class="mt-4 surface-subtle card-contrast p-4 text-sm">
          <div class="text-xs text-mist-300">Top hypothesis</div>
          <div class="mt-2 font-semibold">{report.report.top_hypothesis.statement}</div>
        </div>
      {/if}

      <div class="mt-6">
        <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Recommended actions</div>
        <div class="mt-3 space-y-2 text-sm text-mist-200">
          {#if report?.report?.next_validations && report.report.next_validations.length > 0}
            {#each report.report.next_validations as action}
              <div class="surface-subtle card-contrast p-3">{action}</div>
            {/each}
          {:else}
            <div class="text-mist-300">No actions available.</div>
          {/if}
        </div>
      </div>
    </div>
  </section>
{/if}
