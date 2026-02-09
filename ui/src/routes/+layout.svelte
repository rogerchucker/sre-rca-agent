<script lang="ts">
  import '../app.css';
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { fetchUiMode } from '$lib/api';
  import { incidentTabs } from '$lib/stores/incident-tabs';

  const nav = [
    { href: '/', label: 'Overview' },
    { href: '/systems', label: 'Systems Access' },
    { href: '/knowledge', label: 'Knowledge Base' },
    { href: '/onboarding', label: 'Onboarding' }
  ];
  let liveMode = true;

  onMount(async () => {
    try {
      const res = await fetchUiMode();
      liveMode = res.live_mode;
    } catch {
      liveMode = true;
    }
  });
</script>

<div class="min-h-screen">
  <div class="mx-auto flex max-w-7xl gap-6 px-6 py-6">
    <aside class="hidden w-56 flex-col gap-6 lg:flex">
      <div class="surface px-4 py-5">
        <div class="text-xs text-mist-300">Operations Portal</div>
        <div class="mt-2 text-lg font-semibold">Agentic SRE Control Plane</div>
        <div class="mt-4 badge text-accent-500">{liveMode ? 'Live Mode' : 'Simulation Mode'}</div>
      </div>
      <nav class="surface flex flex-col gap-1 px-3 py-4 text-sm">
        {#each nav as item}
          <a
            href={item.href}
            class={`rounded-lg px-3 py-2 transition ${$page.url.pathname === item.href ? 'bg-ink-700/70 text-accent-500' : 'text-mist-300 hover:text-mist-100'}`}
          >
            {item.label}
          </a>
        {/each}
      </nav>
      <div class="surface-subtle px-4 py-4 text-xs text-mist-300">
        Trust: human approval required<br />
        Env: prod / staging<br />
        Access: read-only by default
      </div>
    </aside>

    <div class="flex-1">
      <main>
        {#if $page.url.pathname === '/' || $page.url.pathname.startsWith('/incident')}
          <div class="tabbar mb-6">
            <div class="flex flex-wrap items-center gap-2">
              {#if $incidentTabs.openTabs.length === 0}
                <div class="text-xs uppercase tracking-[0.3em] text-mist-300">No incidents opened</div>
              {:else}
                {#each $incidentTabs.openTabs as tab}
                  <div class={`tab ${$incidentTabs.activeTabId === tab.id ? 'tab-active' : ''}`}>
                    <button
                      class="tab-button"
                      on:click={() => {
                        incidentTabs.setActive(tab.id);
                        goto(`/incident/${tab.id}`);
                      }}
                    >
                      <span class="tab-title">{tab.title}</span>
                      <span class="tab-meta">{tab.severity} · {tab.environment}</span>
                    </button>
                    <button
                      class="tab-close"
                      aria-label="Close incident tab"
                      on:click={() => {
                        const remaining = $incidentTabs.openTabs.filter((t) => t.id !== tab.id);
                        const nextActive = remaining.length > 0 ? remaining[0].id : null;
                        incidentTabs.closeTab(tab.id);
                        if (tab.id === $incidentTabs.activeTabId) {
                          if (nextActive) {
                            goto(`/incident/${nextActive}`);
                          } else if ($page.url.pathname.startsWith('/incident')) {
                            goto('/');
                          }
                        }
                      }}
                    >
                      ×
                    </button>
                  </div>
                {/each}
              {/if}
              {#if $incidentTabs.openTabs.length >= incidentTabs.maxTabs}
                <div class="ml-auto text-xs text-mist-300">Max {incidentTabs.maxTabs} tabs</div>
              {/if}
            </div>
          </div>
        {/if}
        <slot />
      </main>
    </div>
  </div>
</div>
