<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchIncidentAlerts, fetchIncidentChanges, fetchIncidents, fetchLatestReport, type RCAReportResponse } from '$lib/api';

  let report: RCAReportResponse | null = null;
  let error = '';
  let changes: Array<Record<string, unknown>> = [];
  let alerts: Array<Record<string, unknown>> = [];

  onMount(async () => {
    try {
      const response = await fetchIncidents({ page: 1, page_size: 1 });
      if (response.items.length === 0) {
        error = 'No incidents available.';
        return;
      }
      const incidentId = response.items[0].id;
      report = await fetchLatestReport(incidentId);
      changes = await fetchIncidentChanges(incidentId);
      alerts = await fetchIncidentAlerts(incidentId);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load incident report.';
    }
  });
</script>

<section class="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
  <div class="surface p-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Investigation view</div>
        <div class="mt-2 text-2xl font-semibold">Payments latency spike</div>
      </div>
      <div class="badge text-warning-500">Severity P1</div>
    </div>

    {#if error}
      <div class="mt-4 text-xs text-danger-500">{error}</div>
    {:else if report?.report?.evidence && report.report.evidence.length > 0}
      <div class="mt-6 space-y-4">
        {#each report.report.evidence as item}
          <div class="flex gap-3">
            <div class="mt-2">
              <div class="timeline-dot"></div>
            </div>
            <div>
              <div class="text-xs text-mist-300">{item.time_range.start} · {item.source}</div>
              <div class="text-sm font-semibold">{item.summary}</div>
            </div>
          </div>
        {/each}
      </div>
    {:else}
      <div class="mt-4 text-sm text-mist-300">No evidence timeline available.</div>
    {/if}
  </div>

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
</section>

<section class="mt-6 grid gap-6 lg:grid-cols-2">
  <div class="surface p-6">
    <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Related changes</div>
    <div class="mt-4 space-y-3 text-sm text-mist-200">
      {#if changes.length === 0}
        <div class="surface-subtle card-contrast p-4 text-sm text-mist-300">No related changes available.</div>
      {:else}
        {#each changes as change}
          <div class="surface-subtle card-contrast p-4">{change.summary ?? change.query ?? 'Change item'}</div>
        {/each}
      {/if}
    </div>
  </div>
  <div class="surface p-6">
    <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Related alerts</div>
    <div class="mt-4 space-y-3 text-sm text-mist-200">
      {#if alerts.length === 0}
        <div class="surface-subtle card-contrast p-4 text-sm text-mist-300">No alerts available.</div>
      {:else}
        {#each alerts as alert}
          <div class="surface-subtle card-contrast p-4">{alert.summary ?? alert.query ?? 'Alert item'}</div>
        {/each}
      {/if}
    </div>
  </div>
</section>

<section class="mt-6 surface p-6">
  <div class="flex flex-wrap items-center justify-between gap-3">
    <div>
      <div class="text-xs uppercase tracking-[0.3em] text-mist-300">AI reasoning (read-only)</div>
      <div class="mt-2 text-xl font-semibold">Correlation-backed with uncertainty</div>
    </div>
    <div class="badge text-accent-500">Evidence cited</div>
  </div>
  <p class="mt-4 text-sm text-mist-200">
    {#if report?.report?.top_hypothesis}
      {report.report.top_hypothesis.statement}
    {:else}
      Awaiting RCA output for reasoning details.
    {/if}
  </p>
</section>
