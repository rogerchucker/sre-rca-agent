<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchOnboarding, fetchPatterns, fetchRunbooks } from '$lib/api';

  let onboarding: { subjects: Array<Record<string, unknown>>; providers: Array<Record<string, unknown>> } | null = null;
  let runbooks: Array<{ subject: string; name: string; indicators: string[] }> = [];
  let patterns: Array<{ subject: string; pattern: string; indicators: string[] }> = [];
  let error = '';

  onMount(async () => {
    try {
      onboarding = await fetchOnboarding();
      runbooks = await fetchRunbooks();
      patterns = await fetchPatterns();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to load systems access data.';
    }
  });

  function subjectRunbooks(subject?: string) {
    if (!subject) return [];
    return runbooks.filter((rb) => rb.subject === subject);
  }

  function subjectPatterns(subject?: string) {
    if (!subject) return [];
    return patterns.filter((pt) => pt.subject === subject);
  }
</script>

<section class="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
  <div class="surface p-6">
    <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Systems by service</div>
    <div class="mt-2 text-2xl font-semibold">Access across the ecosystem</div>

    {#if error}
      <div class="mt-4 text-xs text-danger-500">{error}</div>
    {:else if !onboarding}
      <div class="mt-4 text-sm text-mist-300">Loading systems…</div>
    {:else if onboarding.subjects.length === 0}
      <div class="mt-4 text-sm text-mist-300">No subjects onboarded.</div>
    {:else}
      <div class="mt-6 space-y-4">
        {#each onboarding.subjects as subject}
          <div class="surface-subtle card-contrast p-4">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div class="text-sm font-semibold">{subject.name ?? 'subject'}</div>
                <div class="mt-1 text-xs text-mist-300">Environment: {subject.environment ?? 'n/a'}</div>
              </div>
              <div class="text-xs text-mist-300">Bindings: {Object.keys(subject.bindings ?? {}).length}</div>
            </div>
            <div class="mt-3 flex flex-wrap gap-2 text-xs">
              {#each Object.keys(subject.bindings ?? {}) as binding}
                <span class="chip">{binding}</span>
              {/each}
            </div>
            <div class="mt-4 grid gap-3 sm:grid-cols-2">
              <div class="surface-subtle card-contrast p-3">
                <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Runbooks</div>
                <div class="mt-2 space-y-2 text-xs text-mist-200">
                  {#each subjectRunbooks(subject.name) as rb}
                    <div>{rb.name}</div>
                  {/each}
                  {#if subjectRunbooks(subject.name).length === 0}
                    <div class="text-mist-300">None listed</div>
                  {/if}
                </div>
              </div>
              <div class="surface-subtle card-contrast p-3">
                <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Playbooks</div>
                <div class="mt-2 space-y-2 text-xs text-mist-200">
                  {#each subjectPatterns(subject.name) as pt}
                    <div>{pt.pattern}</div>
                  {/each}
                  {#if subjectPatterns(subject.name).length === 0}
                    <div class="text-mist-300">None listed</div>
                  {/if}
                </div>
              </div>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>

  <div class="surface p-6">
    <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Providers & access</div>
    <div class="mt-2 text-2xl font-semibold">Tooling inventory</div>

    {#if error}
      <div class="mt-4 text-xs text-danger-500">{error}</div>
    {:else if !onboarding}
      <div class="mt-4 text-sm text-mist-300">Loading providers…</div>
    {:else if onboarding.providers.length === 0}
      <div class="mt-4 text-sm text-mist-300">No providers onboarded.</div>
    {:else}
      <div class="mt-6 space-y-4">
        {#each onboarding.providers as provider}
          <div class="surface-subtle card-contrast p-4">
            <div class="flex items-center justify-between gap-2">
              <div class="text-sm font-semibold">{provider.id ?? 'provider'}</div>
              <span class="chip">{provider.category ?? 'n/a'}</span>
            </div>
            <div class="mt-2 text-xs text-mist-300">Type: {provider.type ?? 'n/a'}</div>
            <div class="mt-3 text-xs text-mist-200">Capabilities:</div>
            <div class="mt-2 flex flex-wrap gap-2 text-xs">
              {#each Object.keys(provider.capabilities ?? {}) as cap}
                <span class="chip">{cap}</span>
              {/each}
              {#if Object.keys(provider.capabilities ?? {}).length === 0}
                <span class="text-mist-300">No capabilities listed</span>
              {/if}
            </div>
            <div class="mt-3 text-xs text-mist-200">Config (redacted keys):</div>
            <div class="mt-2 flex flex-wrap gap-2 text-xs">
              {#each Object.keys(provider.config ?? {}) as key}
                <span class="chip">{key}</span>
              {/each}
              {#if Object.keys(provider.config ?? {}).length === 0}
                <span class="text-mist-300">No config keys</span>
              {/if}
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>
</section>
