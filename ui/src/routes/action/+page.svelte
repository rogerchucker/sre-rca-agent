<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchIncidents, fetchLatestReport, postAction, type RCAReportResponse } from '$lib/api';

  let report: RCAReportResponse | null = null;
  let error = '';
  let incidentId = '';
  let actionStatus = '';

  onMount(async () => {
    try {
      const response = await fetchIncidents({ page: 1, page_size: 1 });
      if (response.items.length === 0) {
        error = 'No incidents available.';
        return;
      }
      incidentId = response.items[0].id;
      report = await fetchLatestReport(incidentId);
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load actions.';
    }
  });

  async function runDryRun(name: string) {
    if (!incidentId) return;
    actionStatus = '';
    try {
      const res = await postAction({ incident_id: incidentId, name }, 'dry-run');
      actionStatus = `Dry-run ${res.status}`;
    } catch (err) {
      actionStatus = err instanceof Error ? err.message : 'Dry-run failed';
    }
  }
</script>

<section class="surface p-6">
  <div class="flex flex-wrap items-center justify-between gap-3">
    <div>
      <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Action center</div>
      <div class="mt-2 text-2xl font-semibold">Safe operational actions</div>
    </div>
    <div class="badge text-accent-500">Approval gated</div>
  </div>

  <div class="mt-6 grid gap-4 lg:grid-cols-3">
    {#if error}
      <div class="text-xs text-danger-500">{error}</div>
    {:else if report?.report?.next_validations && report.report.next_validations.length > 0}
      {#each report.report.next_validations as actionName}
        <div class="surface-subtle card-contrast p-5">
          <div class="text-sm font-semibold">{actionName}</div>
          <div class="mt-2 text-xs text-mist-300">Risk: Low</div>
          <div class="mt-3 flex flex-wrap gap-2 text-xs">
            <span class="rounded-full border border-ink-700/60 px-2 py-1">Dry-run available</span>
            <span class="rounded-full border border-warning-500/60 px-2 py-1 text-warning-500">Approval required</span>
          </div>
          <button class="mt-4 w-full button-contrast" on:click={() => runDryRun(actionName)}>
            Preview blast radius
          </button>
        </div>
      {/each}
    {:else}
      <div class="text-sm text-mist-300">No actions available.</div>
    {/if}
  </div>
  {#if actionStatus}
    <div class="mt-4 text-xs text-mist-300">{actionStatus}</div>
  {/if}
</section>

<section class="mt-6 surface p-6">
  <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Policy gate</div>
  <div class="mt-3 text-sm text-mist-200">
    Destructive actions require explicit human approval. Demo mode executes against a sandbox environment and
    displays simulation banners across the UI.
  </div>
</section>
