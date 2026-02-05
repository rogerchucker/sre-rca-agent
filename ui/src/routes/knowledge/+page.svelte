<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchOnboarding, fetchPatterns, fetchRunbooks } from '$lib/api';

  let patterns: Array<{ subject: string; pattern: string; indicators: string[] }> = [];
  let runbooks: Array<{ subject: string; name: string; indicators: string[] }> = [];
  let onboarding: { subjects: Array<Record<string, unknown>> } | null = null;
  let error = '';
  let subjectFilter = 'all';

  onMount(async () => {
    try {
      patterns = await fetchPatterns();
      runbooks = await fetchRunbooks();
      onboarding = await fetchOnboarding();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load knowledge base.';
    }
  });

  $: subjects = onboarding?.subjects?.map((s) => s.name).filter(Boolean) ?? [];
  $: filteredRunbooks = subjectFilter === 'all' ? runbooks : runbooks.filter((rb) => rb.subject === subjectFilter);
  $: filteredPatterns = subjectFilter === 'all' ? patterns : patterns.filter((pt) => pt.subject === subjectFilter);
</script>

<section class="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
  <div class="surface p-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Knowledge base</div>
        <div class="mt-2 text-2xl font-semibold">Runbooks & playbooks</div>
      </div>
      <div>
        <label class="text-xs text-mist-300" for="subjectFilter">Filter by subject</label>
        <select
          id="subjectFilter"
          class="ml-2 rounded-lg border border-ink-600/80 bg-ink-800/70 px-2 py-1 text-xs text-mist-100"
          bind:value={subjectFilter}
        >
          <option value="all">All</option>
          {#each subjects as subject}
            <option value={subject}>{subject}</option>
          {/each}
        </select>
      </div>
    </div>

    {#if error}
      <div class="mt-4 text-xs text-danger-500">{error}</div>
    {/if}

    <div class="mt-6 grid gap-4 lg:grid-cols-2">
      <div class="surface-subtle card-contrast p-4">
        <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Runbooks</div>
        <div class="mt-4 space-y-3 text-sm">
          {#if filteredRunbooks.length === 0}
            <div class="text-mist-300">No runbooks available.</div>
          {:else}
            {#each filteredRunbooks as runbook}
              <div class="surface-subtle card-contrast p-3">
                <div class="text-sm font-semibold">{runbook.name}</div>
                <div class="mt-1 text-xs text-mist-300">Subject: {runbook.subject}</div>
              </div>
            {/each}
          {/if}
        </div>
      </div>

      <div class="surface-subtle card-contrast p-4">
        <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Playbooks</div>
        <div class="mt-4 space-y-3 text-sm">
          {#if filteredPatterns.length === 0}
            <div class="text-mist-300">No playbooks available.</div>
          {:else}
            {#each filteredPatterns as pattern}
              <div class="surface-subtle card-contrast p-3">
                <div class="text-sm font-semibold">{pattern.pattern}</div>
                <div class="mt-1 text-xs text-mist-300">Subject: {pattern.subject}</div>
              </div>
            {/each}
          {/if}
        </div>
      </div>
    </div>
  </div>

  <div class="surface p-6">
    <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Coverage</div>
    <div class="mt-2 text-2xl font-semibold">Knowledge base inventory</div>

    <div class="mt-6 space-y-4">
      <div class="kpi">
        <div class="kpi-title">Subjects onboarded</div>
        <div class="kpi-value">{onboarding?.subjects?.length ?? 0}</div>
      </div>
      <div class="kpi">
        <div class="kpi-title">Runbooks</div>
        <div class="kpi-value">{runbooks.length}</div>
      </div>
      <div class="kpi">
        <div class="kpi-title">Playbooks</div>
        <div class="kpi-value">{patterns.length}</div>
      </div>
    </div>
  </div>
</section>
