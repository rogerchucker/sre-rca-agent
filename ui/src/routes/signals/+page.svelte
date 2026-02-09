<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchIncidents, fetchLatestReport, fetchSignalsCorrelation, fetchSignalsTimeline, type RCAReportResponse } from '$lib/api';

  let report: RCAReportResponse | null = null;
  let error = '';
  let timeline: Array<{ time: string; label: string; source: string; kind: string }> = [];
  let correlation: Array<{ pair: string; score: number }> = [];

  onMount(async () => {
    try {
      const response = await fetchIncidents({ page: 1, page_size: 1 });
      if (response.items.length === 0) {
        error = 'No incidents available.';
        return;
      }
      const incidentId = response.items[0].id;
      report = await fetchLatestReport(incidentId);
      timeline = await fetchSignalsTimeline(incidentId);
      const corr = await fetchSignalsCorrelation(incidentId);
      correlation = corr.pairs;
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load signals.';
    }
  });
</script>

<section class="surface p-6">
  <div class="flex flex-wrap items-center justify-between gap-3">
    <div>
      <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Signals explorer</div>
      <div class="mt-2 text-2xl font-semibold">Cross-signal correlation</div>
    </div>
    <div class="flex flex-wrap items-center gap-2 text-xs">
      <span class="rounded-full border border-ink-700/60 px-3 py-1">Last 2h</span>
      <span class="rounded-full border border-ink-700/60 px-3 py-1">Payments</span>
      <span class="rounded-full border border-ink-700/60 px-3 py-1">prod</span>
    </div>
  </div>

  <div class="mt-6 grid gap-4 lg:grid-cols-[1.2fr_1fr]">
    <div class="surface-subtle card-contrast p-5">
      <div class="text-xs text-mist-300">Unified timeline</div>
      {#if error}
        <div class="mt-4 text-xs text-danger-500">{error}</div>
      {:else if timeline.length > 0}
        <div class="mt-4 space-y-4">
          {#each timeline as item}
            <div class="flex gap-3">
              <div class="mt-2">
                <div class="timeline-dot"></div>
              </div>
              <div>
                <div class="text-xs text-mist-300">{item.time} · {item.source}</div>
                <div class="text-sm font-semibold">{item.label}</div>
              </div>
            </div>
          {/each}
        </div>
      {:else}
        <div class="mt-4 text-sm text-mist-300">No evidence timeline available.</div>
      {/if}
    </div>
    <div class="surface-subtle card-contrast p-5">
      <div class="text-xs text-mist-300">Correlation graph</div>
      <div class="mt-4 grid gap-3 text-sm text-mist-200">
        {#if correlation.length === 0}
          <div class="surface-subtle card-contrast px-4 py-3">No correlation data yet.</div>
        {:else}
          {#each correlation as pair}
            <div class="surface-subtle card-contrast px-4 py-3">{pair.pair} score {pair.score.toFixed(2)}</div>
          {/each}
        {/if}
      </div>
      <div class="mt-4 text-xs text-mist-300">
        Evidence pinned: 6 · Exportable timeline ready
      </div>
    </div>
  </div>
</section>
