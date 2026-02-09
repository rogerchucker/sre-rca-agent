<script lang="ts">
  import { onMount } from 'svelte';
  import {
    fetchAttention,
    fetchHealth,
    fetchIncidents,
    postIncident,
    type IncidentListItem
  } from '$lib/api';
  import { incidentTabs } from '$lib/stores/incident-tabs';
  import { goto } from '$app/navigation';

  let healthStatus: 'idle' | 'ok' | 'error' = 'idle';
  let healthError = '';
  let incidentError = '';
  let loadingIncident = false;
  let incidents: IncidentListItem[] = [];
  let attention: Array<{ id: string; title: string; severity: string; environment: string; updated_at: string }> = [];
  let incidentsError = '';
  let attentionError = '';

  let completedDay = 0;
  let completedMonth = 0;
  let avgResolve = 0;

  const demoPayload = {
    title: 'Payment latency spike in us-west-2',
    severity: 'P1',
    environment: 'prod',
    subject: 'payments-api',
    labels: { region: 'us-west-2', team: 'payments' },
    annotations: { runbook: 'rbk-payments-latency' }
  };

  function parseTime(value?: string | null) {
    if (!value) return null;
    const d = new Date(value);
    return Number.isNaN(d.getTime()) ? null : d;
  }

  function computeStats(items: IncidentListItem[]) {
    const now = Date.now();
    const dayAgo = now - 24 * 60 * 60 * 1000;
    const monthAgo = now - 30 * 24 * 60 * 60 * 1000;

    const completed = items.filter((item) => {
      const end = parseTime(item.ends_at);
      return end && end.getTime() <= now;
    });

    completedDay = completed.filter((item) => {
      const end = parseTime(item.ends_at);
      return end && end.getTime() >= dayAgo;
    }).length;

    completedMonth = completed.filter((item) => {
      const end = parseTime(item.ends_at);
      return end && end.getTime() >= monthAgo;
    }).length;

    const durations = completed
      .map((item) => {
        const start = parseTime(item.starts_at);
        const end = parseTime(item.ends_at);
        if (!start || !end) return null;
        return end.getTime() - start.getTime();
      })
      .filter((val): val is number => val !== null && val >= 0);

    avgResolve = durations.length > 0 ? durations.reduce((a, b) => a + b, 0) / durations.length : 0;
  }

  function formatDuration(ms: number) {
    if (!ms) return '—';
    const minutes = Math.round(ms / 60000);
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.round(minutes / 60);
    if (hours < 24) return `${hours}h`;
    const days = Math.round(hours / 24);
    return `${days}d`;
  }

  function isActive(incident: IncidentListItem) {
    const end = parseTime(incident.ends_at);
    if (!end) return true;
    return end.getTime() > Date.now();
  }

  onMount(async () => {
    try {
      const res = await fetchHealth();
      healthStatus = res.ok ? 'ok' : 'error';
    } catch (err) {
      healthStatus = 'error';
      healthError = err instanceof Error ? err.message : 'Unknown error';
    }

    try {
      const response = await fetchIncidents({ page: 1, page_size: 20 });
      incidents = response.items;
      computeStats(incidents);
    } catch (err) {
      incidentsError = err instanceof Error ? err.message : 'Unable to load incidents';
    }

    try {
      attention = await fetchAttention(5);
    } catch (err) {
      attentionError = err instanceof Error ? err.message : 'Unable to load attention queue';
    }
  });

  async function runDemo() {
    incidentError = '';
    loadingIncident = true;
    try {
      await postIncident(demoPayload);
      const response = await fetchIncidents({ page: 1, page_size: 20 });
      incidents = response.items;
      computeStats(incidents);
    } catch (err) {
      incidentError = err instanceof Error ? err.message : 'Unknown error';
    } finally {
      loadingIncident = false;
    }
  }

  function openIncident(incident: IncidentListItem) {
    incidentTabs.openTab({
      id: incident.id,
      title: incident.title,
      severity: incident.severity,
      environment: incident.environment,
      subject: incident.subject
    });
    goto(`/incident/${incident.id}`);
  }
</script>

<section class="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
  <div class="surface p-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Agent performance</div>
        <div class="mt-2 text-2xl font-semibold">Investigation throughput & reliability</div>
      </div>
      <div class="rounded-full border border-ink-500/80 bg-ink-800/70 px-4 py-2 text-xs text-mist-100">
        API Health: {healthStatus === 'ok' ? 'Connected' : healthStatus === 'error' ? 'Degraded' : 'Checking'}
      </div>
    </div>
    {#if healthError}
      <div class="mt-3 text-xs text-danger-500">{healthError}</div>
    {/if}

    <div class="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <div class="kpi">
        <div class="kpi-title">Completed (24h)</div>
        <div class="kpi-value">{completedDay}</div>
      </div>
      <div class="kpi">
        <div class="kpi-title">Completed (30d)</div>
        <div class="kpi-value">{completedMonth}</div>
      </div>
      <div class="kpi">
        <div class="kpi-title">Avg resolve time</div>
        <div class="kpi-value">{formatDuration(avgResolve)}</div>
      </div>
      <div class="kpi" title="Not instrumented">
        <div class="kpi-title">Avg reopens</div>
        <div class="kpi-value">—</div>
      </div>
    </div>
  </div>

  <div class="surface p-6">
    <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Live RCA</div>
    <div class="mt-2 text-xl font-semibold">Run RCA on a live incident</div>
    <p class="mt-3 text-sm text-mist-200">
      Trigger an investigation, gather evidence, and produce a recommendation. The report will appear in the incident
      tab bar.
    </p>
    <button class="mt-4 w-full button-contrast" on:click={runDemo} disabled={loadingIncident}>
      {loadingIncident ? 'Running RCA...' : 'Run Demo RCA'}
    </button>
    {#if incidentError}
      <div class="mt-3 text-xs text-danger-500">{incidentError}</div>
    {/if}

    <div class="mt-6 border-t border-ink-700/70 pt-6">
      <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Attention queue</div>
      <div class="mt-4 space-y-3">
        {#if attentionError}
          <div class="text-xs text-danger-500">{attentionError}</div>
        {:else if attention.length === 0}
          <div class="surface-subtle card-contrast p-4 text-sm text-mist-300">No items in attention queue.</div>
        {:else}
          {#each attention as item}
            <div class="surface-subtle card-contrast p-4">
              <div class="flex items-center justify-between text-xs text-mist-300">
                <span>{item.id}</span>
                <span>{item.updated_at}</span>
              </div>
              <div class="mt-2 text-sm font-semibold">{item.title}</div>
              <div class="mt-2 flex items-center gap-2 text-xs text-mist-300">
                <span class="chip">{item.severity}</span>
                <span>{item.environment}</span>
              </div>
            </div>
          {/each}
        {/if}
      </div>
    </div>
  </div>
</section>

<section class="mt-6 surface p-6">
  <div class="flex flex-wrap items-center justify-between gap-3">
    <div>
      <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Recent investigations</div>
      <div class="mt-2 text-xl font-semibold">Latest investigations across the fleet</div>
    </div>
    <div class="text-xs text-mist-300">Showing {incidents.length} records</div>
  </div>

  {#if incidentsError}
    <div class="mt-4 text-xs text-danger-500">{incidentsError}</div>
  {:else if incidents.length === 0}
    <div class="mt-4 text-sm text-mist-300">No investigations available.</div>
  {:else}
    <div class="mt-6 scroll-list">
      {#each incidents as incident}
        <button class="list-row" on:click={() => openIncident(incident)}>
          <div class="flex items-center gap-3">
            <span class={`status-dot ${isActive(incident) ? 'status-dot-active' : ''}`}></span>
            <div>
              <div class="text-sm font-semibold">{incident.title}</div>
              <div class="mt-1 text-xs text-mist-300">{incident.subject} · {incident.environment}</div>
            </div>
          </div>
          <div class="flex items-center gap-2 text-xs text-mist-300">
            <span class="chip">{incident.severity}</span>
            <span>{isActive(incident) ? 'Active' : 'Resolved'}</span>
          </div>
        </button>
      {/each}
    </div>
  {/if}
</section>
