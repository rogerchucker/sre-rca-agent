<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import React from 'react';
  import { createRoot, type Root } from 'react-dom/client';
  import type { OnboardingModel } from '$lib/api';

  export let model: OnboardingModel;
  export let loading = false;
  export let onPreview: () => Promise<void>;
  export let onApply: () => Promise<void>;
  export let onPlanIntent: (intent: string) => Promise<string>;
  export let onApplyPlanned: () => Promise<string>;
  export let onRejectPlanned: () => string;

  let host: HTMLDivElement;
  let portalHost: HTMLDivElement | null = null;
  let root: Root | null = null;
  let OnboardingCopilotComponent: React.ComponentType<any> | null = null;

  function render() {
    if (!root || !OnboardingCopilotComponent) return;
    root.render(
      React.createElement(OnboardingCopilotComponent, {
        model,
        loading,
        onPreview,
        onApply,
        onPlanIntent,
        onApplyPlanned,
        onRejectPlanned
      })
    );
  }

  onMount(async () => {
    // CopilotKit's popup uses `position: fixed`, but CSS containing blocks (e.g. filters/backdrop-filter)
    // can cause unexpected clipping when the React tree is mounted inside complex page chrome.
    // Mount into `document.body` to keep the popup anchored to the viewport.
    portalHost = document.createElement('div');
    portalHost.setAttribute('data-copilot-portal', 'true');
    document.body.appendChild(portalHost);

    root = createRoot(portalHost);
    const module = await import('$lib/copilot/OnboardingCopilot');
    OnboardingCopilotComponent = module.OnboardingCopilot;
    render();
  });

  onDestroy(() => {
    if (root) {
      root.unmount();
      root = null;
    }
    if (portalHost?.parentNode) {
      portalHost.parentNode.removeChild(portalHost);
    }
    portalHost = null;
  });

  $: render();
</script>

<div bind:this={host}></div>
