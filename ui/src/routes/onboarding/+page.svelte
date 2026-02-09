<script lang="ts">
  import { onMount } from 'svelte';
  import {
    applyOnboardingModel,
    applyOnboardingOps,
    fetchOnboardingModelByProfile,
    planOnboardingChanges,
    type BindingResolution,
    type OnboardingAgentOp,
    previewOnboardingModel,
    type OnboardingFailureModeModel,
    type OnboardingModel,
    type OnboardingProfile,
    type OnboardingProviderModel,
    type OnboardingSubjectModel,
    type ResolvedSubjectBindings
  } from '$lib/api';
  import CopilotHost from '$lib/components/CopilotHost.svelte';

  let model: OnboardingModel = { providers: [], subjects: [] };
  let resolvedBindings: ResolvedSubjectBindings[] = [];
  let availableCapabilities: string[] = [];
  let profile: OnboardingProfile = 'template';
  let errors: string[] = [];
  let status = '';
  let loading = false;
  let paths = { catalog: '', kb: '' };
  let sourcePaths = { catalog: '', kb: '' };
  let diffs = { catalog: '', kb: '' };
  let yamlPreview = { catalog: '', kb: '' };
  let providerConfigDrafts: Record<number, string> = {};
  let providerConfigErrors: Record<number, string> = {};

  let assistantProposedOps: OnboardingAgentOp[] = [];
  let assistantAppliedOps: OnboardingAgentOp[] = [];
  let assistantRejectedOps: OnboardingAgentOp[] = [];
  let assistantWarnings: string[] = [];
  let assistantStatus = 'No pending assistant transaction.';
  let lastValidationStatus = 'Not validated yet.';

  const operationPresets: Record<string, string[]> = {
    log_store: ['query.signature_counts', 'query.samples'],
    metrics_store: ['query_range'],
    trace_store: ['search_traces'],
    deploy_tracker: ['list_deployments', 'get_deployment_metadata'],
    vcs: ['list_changes'],
    alerting: ['list_alerts']
  };

  onMount(async () => {
    const saved = window.localStorage.getItem('onboarding_profile');
    if (saved === 'template' || saved === 'demo') {
      profile = saved;
    }
    await loadModel(profile);
  });

  async function loadModel(nextProfile: OnboardingProfile = profile) {
    loading = true;
    status = '';
    try {
      const res = await fetchOnboardingModelByProfile(nextProfile);
      profile = res.profile;
      model = res.model;
      resolvedBindings = res.resolved_bindings;
      availableCapabilities = res.available_binding_capabilities;
      paths = { catalog: res.catalog_path, kb: res.kb_path };
      sourcePaths = { catalog: res.source_catalog_path, kb: res.source_kb_path };
      resetProviderDrafts();
      resetAssistantTransaction();
      window.localStorage.setItem('onboarding_profile', profile);
    } catch (err) {
      status = err instanceof Error ? err.message : 'Failed to load onboarding model.';
    } finally {
      loading = false;
    }
  }

  function updateProvider(index: number, patch: Partial<OnboardingProviderModel>) {
    model = {
      ...model,
      providers: model.providers.map((provider, i) => (i === index ? { ...provider, ...patch } : provider))
    };
  }

  function updateSubject(index: number, patch: Partial<OnboardingSubjectModel>) {
    model = {
      ...model,
      subjects: model.subjects.map((subject, i) => (i === index ? { ...subject, ...patch } : subject))
    };
  }

  function parseList(raw: string): string[] {
    return raw
      .split(',')
      .map((value) => value.trim())
      .filter(Boolean);
  }

  function stringifyList(values: string[]): string {
    return values.join(', ');
  }

  function parseJsonObject(raw: string): Record<string, unknown> {
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error('Config JSON must be an object');
    }
    return parsed as Record<string, unknown>;
  }

  function resetAssistantTransaction() {
    assistantProposedOps = [];
    assistantAppliedOps = [];
    assistantRejectedOps = [];
    assistantWarnings = [];
    assistantStatus = 'No pending assistant transaction.';
  }

  function resetProviderDrafts() {
    providerConfigDrafts = {};
    providerConfigErrors = {};
    model.providers.forEach((provider, index) => {
      providerConfigDrafts[index] = JSON.stringify(provider.config, null, 2);
    });
  }

  function onProviderConfigInput(index: number, value: string) {
    providerConfigDrafts = { ...providerConfigDrafts, [index]: value };
    try {
      const parsed = parseJsonObject(value);
      providerConfigErrors = { ...providerConfigErrors, [index]: '' };
      updateProvider(index, { config: parsed });
    } catch (err) {
      providerConfigErrors = {
        ...providerConfigErrors,
        [index]: err instanceof Error ? err.message : 'Invalid JSON'
      };
    }
  }

  function hasConfigErrors(): boolean {
    return Object.values(providerConfigErrors).some((value) => value && value.length > 0);
  }

  function presetOperations(category: string): string[] {
    return operationPresets[category] ? [...operationPresets[category]] : [];
  }

  function capabilityOptions(): string[] {
    const merged = new Set([...availableCapabilities, ...Object.keys(operationPresets)]);
    return Array.from(merged).sort();
  }

  function compatibleProviders(capability: string): OnboardingProviderModel[] {
    return model.providers.filter((provider) => provider.category === capability);
  }

  function allBoundProviderIds(): Set<string> {
    const ids = new Set<string>();
    for (const subject of model.subjects) {
      for (const providerId of Object.values(subject.bindings)) {
        ids.add(providerId);
      }
    }
    return ids;
  }

  function unusedProviderIds(): string[] {
    const bound = allBoundProviderIds();
    return model.providers.map((provider) => provider.id).filter((providerId) => !bound.has(providerId));
  }

  function bindingStatus(item: BindingResolution): 'OK' | 'Unresolved Provider' | 'Category Mismatch' {
    if (!item.resolved) return 'Unresolved Provider';
    if (item.provider_category !== item.capability) return 'Category Mismatch';
    return 'OK';
  }

  function missingCapabilities(subject: OnboardingSubjectModel): string[] {
    return capabilityOptions().filter((capability) => !subject.bindings[capability]);
  }

  function onProfileChange(next: string) {
    if (next !== 'template' && next !== 'demo') return;
    if (next === profile) return;
    profile = next;
    void loadModel(profile);
  }

  function addProvider() {
    const defaultCategory = 'log_store';
    model = {
      ...model,
      providers: [
        ...model.providers,
        {
          id: `provider_${model.providers.length + 1}`,
          category: defaultCategory,
          type: 'custom',
          operations: presetOperations(defaultCategory),
          config: {}
        }
      ]
    };
    resetProviderDrafts();
  }

  function removeProvider(index: number) {
    const providerId = model.providers[index]?.id;
    model = {
      ...model,
      providers: model.providers.filter((_, i) => i !== index),
      subjects: model.subjects.map((subject) => {
        const nextBindings = { ...subject.bindings };
        for (const [capability, boundProviderId] of Object.entries(nextBindings)) {
          if (boundProviderId === providerId) {
            delete nextBindings[capability];
          }
        }
        return { ...subject, bindings: nextBindings };
      })
    };
    resetProviderDrafts();
  }

  function addSubject() {
    model = {
      ...model,
      subjects: [
        ...model.subjects,
        {
          name: `subject-${model.subjects.length + 1}`,
          environment: 'prod',
          aliases: [],
          bindings: {},
          dependencies: [],
          runbooks: [],
          known_failure_modes: [],
          deploy_context: {},
          vcs_context: {},
          log_evidence: {}
        }
      ]
    };
  }

  function removeSubject(index: number) {
    model = {
      ...model,
      subjects: model.subjects.filter((_, i) => i !== index)
    };
  }

  function addFailureMode(subjectIndex: number) {
    const subject = model.subjects[subjectIndex];
    const next: OnboardingFailureModeModel[] = [
      ...subject.known_failure_modes,
      { name: 'new_failure_mode', indicators: [] }
    ];
    updateSubject(subjectIndex, { known_failure_modes: next });
  }

  function updateFailureMode(subjectIndex: number, modeIndex: number, patch: Partial<OnboardingFailureModeModel>) {
    const subject = model.subjects[subjectIndex];
    const next = subject.known_failure_modes.map((mode, i) => (i === modeIndex ? { ...mode, ...patch } : mode));
    updateSubject(subjectIndex, { known_failure_modes: next });
  }

  function removeFailureMode(subjectIndex: number, modeIndex: number) {
    const subject = model.subjects[subjectIndex];
    const next = subject.known_failure_modes.filter((_, i) => i !== modeIndex);
    updateSubject(subjectIndex, { known_failure_modes: next });
  }

  function addBinding(subjectIndex: number) {
    const subject = model.subjects[subjectIndex];
    const options = capabilityOptions();
    const firstMissingCapability = options.find((capability) => !subject.bindings[capability]) ?? 'log_store';
    const firstProvider = compatibleProviders(firstMissingCapability)[0]?.id ?? '';
    const nextBindings = { ...subject.bindings, [firstMissingCapability]: firstProvider };
    updateSubject(subjectIndex, { bindings: nextBindings });
  }

  function removeBinding(subjectIndex: number, capability: string) {
    const subject = model.subjects[subjectIndex];
    const nextBindings = { ...subject.bindings };
    delete nextBindings[capability];
    updateSubject(subjectIndex, { bindings: nextBindings });
  }

  async function onAssistantPlanIntent(intent: string): Promise<string> {
    if (hasConfigErrors()) {
      assistantStatus = 'Resolve provider config JSON errors before using the assistant planner.';
      return assistantStatus;
    }
    try {
      const response = await planOnboardingChanges({
        intent,
        model,
        policy: {
          allow_add_provider: true,
          allow_add_subject: true,
          allow_bindings: true,
          enforce_category_match: true
        }
      });
      assistantProposedOps = response.proposed_ops;
      assistantAppliedOps = response.applied_ops;
      assistantRejectedOps = response.rejected_ops;
      assistantWarnings = response.warnings;
      assistantStatus =
        response.proposed_ops.length > 0
          ? `Proposed ${response.proposed_ops.length} operation(s). Review and apply from transaction panel.`
          : 'No actionable operation proposed.';
      return assistantStatus;
    } catch (err) {
      assistantStatus = err instanceof Error ? err.message : 'Assistant planning failed.';
      return assistantStatus;
    }
  }

  async function onAssistantApplyPlanned(): Promise<string> {
    if (assistantProposedOps.length === 0) {
      assistantStatus = 'No pending proposed operations to apply.';
      return assistantStatus;
    }
    if (hasConfigErrors()) {
      assistantStatus = 'Resolve provider config JSON errors before applying proposed operations.';
      return assistantStatus;
    }
    try {
      const response = await applyOnboardingOps({
        model,
        ops: assistantProposedOps,
        policy: {
          allow_add_provider: true,
          allow_add_subject: true,
          allow_bindings: true,
          enforce_category_match: true
        }
      });
      model = response.model;
      resolvedBindings = response.resolved_bindings;
      assistantAppliedOps = response.applied_ops;
      assistantRejectedOps = response.rejected_ops;
      assistantWarnings = response.warnings;
      assistantStatus = `Applied ${response.applied_ops.length} operation(s), rejected ${response.rejected_ops.length}.`;
      assistantProposedOps = [];
      resetProviderDrafts();
      return assistantStatus;
    } catch (err) {
      assistantStatus = err instanceof Error ? err.message : 'Applying proposed operations failed.';
      return assistantStatus;
    }
  }

  function onAssistantRejectPlanned(): string {
    assistantRejectedOps = [...assistantRejectedOps, ...assistantProposedOps];
    assistantProposedOps = [];
    assistantStatus = 'Rejected pending proposed operations.';
    return assistantStatus;
  }

  async function handlePreview() {
    if (hasConfigErrors()) {
      status = 'Resolve provider config JSON errors before preview.';
      return;
    }
    loading = true;
    status = '';
    errors = [];
    try {
      const res = await previewOnboardingModel({ model });
      errors = res.errors;
      diffs = res.diffs;
      yamlPreview = { catalog: res.yaml.catalog_yaml, kb: res.yaml.kb_yaml };
      resolvedBindings = res.resolved_bindings;
      status = res.ok ? 'Validation passed. Review bindings and diffs before apply.' : 'Validation failed.';
      lastValidationStatus = status;
    } catch (err) {
      status = err instanceof Error ? err.message : 'Preview failed.';
      lastValidationStatus = status;
    } finally {
      loading = false;
    }
  }

  async function handleApply() {
    if (hasConfigErrors()) {
      status = 'Resolve provider config JSON errors before apply.';
      return;
    }
    loading = true;
    status = '';
    errors = [];
    try {
      const res = await applyOnboardingModel({ model });
      resolvedBindings = res.resolved_bindings;
      status = `Applied successfully at ${res.updated_at}. Backups created.`;
      diffs = { catalog: '', kb: '' };
      lastValidationStatus = 'Last apply succeeded.';
    } catch (err) {
      status = err instanceof Error ? err.message : 'Apply failed.';
      lastValidationStatus = status;
    } finally {
      loading = false;
    }
  }
</script>

<section class="grid gap-6">
  <div class="surface p-6">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Onboarding Studio</div>
        <div class="mt-2 text-2xl font-semibold">Providers, subjects, and bindings</div>
      </div>
      <div class="text-xs text-mist-300 space-y-1">
        <div class="flex items-center gap-2">
          <span>Profile</span>
          <select
            class="rounded-lg border border-ink-600/80 bg-ink-900/70 px-2 py-1 text-xs"
            bind:value={profile}
            on:change={(e) => onProfileChange(e.currentTarget.value)}
          >
            <option value="template">Template</option>
            <option value="demo">Demo</option>
          </select>
        </div>
        {#if paths.catalog}
          <div>Catalog: {paths.catalog}</div>
        {/if}
        {#if paths.kb}
          <div>KB: {paths.kb}</div>
        {/if}
        {#if sourcePaths.catalog}
          <div class="text-mist-400">Source catalog: {sourcePaths.catalog}</div>
        {/if}
        {#if sourcePaths.kb}
          <div class="text-mist-400">Source KB: {sourcePaths.kb}</div>
        {/if}
      </div>
    </div>

    {#if status}
      <div class="mt-4 text-xs text-mist-100">{status}</div>
    {/if}

    {#if errors.length > 0}
      <div class="mt-4 space-y-1 text-xs text-danger-400">
        {#each errors as err}
          <div>• {err}</div>
        {/each}
      </div>
    {/if}
    <div class="mt-3 text-xs text-mist-300">Last validation: {lastValidationStatus}</div>
    {#if hasConfigErrors()}
      <div class="mt-2 text-xs text-danger-400">Resolve provider config JSON errors before preview/apply.</div>
    {/if}

    <div class="mt-5 flex flex-wrap gap-3">
      <button class="badge bg-ink-700 px-4 py-2 text-xs text-mist-100" on:click={handlePreview} disabled={loading}>
        {loading ? 'Working...' : 'Preview + Validate'}
      </button>
      <button class="badge bg-accent-500/20 px-4 py-2 text-xs text-accent-200" on:click={handleApply} disabled={loading}>
        Apply changes
      </button>
    </div>
  </div>

  <div class="grid gap-6 xl:grid-cols-2">
    <div class="surface p-6">
      <div class="flex items-center justify-between">
        <div>
          <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Providers</div>
          <div class="mt-1 text-lg font-semibold">Integration instances</div>
        </div>
        <button class="badge bg-ink-700 px-3 py-1 text-xs text-mist-100" on:click={addProvider}>Add provider</button>
      </div>
      <div class="mt-4 space-y-4">
        {#if model.providers.length === 0}
          <div class="text-xs text-mist-300">No providers configured.</div>
        {/if}
        {#each model.providers as provider, providerIndex}
          <div class="surface-subtle card-contrast p-4">
            <div class="flex items-center justify-between gap-2">
              <div class="text-sm font-semibold">{provider.id || `Provider ${providerIndex + 1}`}</div>
              <button class="text-xs text-danger-400" on:click={() => removeProvider(providerIndex)}>Remove</button>
            </div>
            <div class="mt-3 grid gap-3 md:grid-cols-3">
              <label class="text-xs">
                <div class="text-mist-300">ID</div>
                <input class="mt-1 w-full rounded-lg border border-ink-600/80 bg-ink-900/70 px-2 py-1" value={provider.id} on:input={(e) => updateProvider(providerIndex, { id: e.currentTarget.value })} />
              </label>
              <label class="text-xs">
                <div class="text-mist-300">Category</div>
                <select
                  class="mt-1 w-full rounded-lg border border-ink-600/80 bg-ink-900/70 px-2 py-1"
                  value={provider.category}
                  on:change={(e) => {
                    const nextCategory = e.currentTarget.value;
                    const nextOps = provider.operations.length > 0 ? provider.operations : presetOperations(nextCategory);
                    updateProvider(providerIndex, { category: nextCategory, operations: nextOps });
                  }}
                >
                  {#each capabilityOptions() as capability}
                    <option value={capability}>{capability}</option>
                  {/each}
                </select>
              </label>
              <label class="text-xs">
                <div class="text-mist-300">Type</div>
                <input class="mt-1 w-full rounded-lg border border-ink-600/80 bg-ink-900/70 px-2 py-1" value={provider.type} on:input={(e) => updateProvider(providerIndex, { type: e.currentTarget.value })} />
              </label>
            </div>
            <label class="mt-3 block text-xs">
              <div class="flex items-center justify-between text-mist-300">
                <span>Operations (comma separated)</span>
                <button
                  class="text-accent-300"
                  on:click={() => updateProvider(providerIndex, { operations: presetOperations(provider.category) })}
                >
                  Use preset
                </button>
              </div>
              <input class="mt-1 w-full rounded-lg border border-ink-600/80 bg-ink-900/70 px-2 py-1" value={stringifyList(provider.operations)} on:input={(e) => updateProvider(providerIndex, { operations: parseList(e.currentTarget.value) })} />
            </label>
            <label class="mt-3 block text-xs">
              <div class="text-mist-300">Config JSON</div>
              <textarea
                class="mt-1 h-28 w-full rounded-lg border border-ink-600/80 bg-ink-900/70 p-2"
                spellcheck="false"
                value={providerConfigDrafts[providerIndex] ?? JSON.stringify(provider.config, null, 2)}
                on:input={(e) => onProviderConfigInput(providerIndex, e.currentTarget.value)}
              ></textarea>
              {#if providerConfigErrors[providerIndex]}
                <div class="mt-1 text-danger-400">{providerConfigErrors[providerIndex]}</div>
              {/if}
            </label>
          </div>
        {/each}
      </div>
    </div>

    <div class="surface p-6">
      <div class="flex items-center justify-between">
        <div>
          <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Subjects</div>
          <div class="mt-1 text-lg font-semibold">Service definitions</div>
        </div>
        <button class="badge bg-ink-700 px-3 py-1 text-xs text-mist-100" on:click={addSubject}>Add subject</button>
      </div>
      <div class="mt-4 space-y-4">
        {#if model.subjects.length === 0}
          <div class="text-xs text-mist-300">No subjects configured.</div>
        {/if}
        {#each model.subjects as subject, subjectIndex}
          <div class="surface-subtle card-contrast p-4">
            <div class="flex items-center justify-between gap-2">
              <div class="text-sm font-semibold">{subject.name || `Subject ${subjectIndex + 1}`}</div>
              <button class="text-xs text-danger-400" on:click={() => removeSubject(subjectIndex)}>Remove</button>
            </div>
            <div class="mt-3 grid gap-3 md:grid-cols-2">
              <label class="text-xs">
                <div class="text-mist-300">Name</div>
                <input class="mt-1 w-full rounded-lg border border-ink-600/80 bg-ink-900/70 px-2 py-1" value={subject.name} on:input={(e) => updateSubject(subjectIndex, { name: e.currentTarget.value })} />
              </label>
              <label class="text-xs">
                <div class="text-mist-300">Environment</div>
                <input class="mt-1 w-full rounded-lg border border-ink-600/80 bg-ink-900/70 px-2 py-1" value={subject.environment} on:input={(e) => updateSubject(subjectIndex, { environment: e.currentTarget.value })} />
              </label>
            </div>
            <label class="mt-3 block text-xs">
              <div class="text-mist-300">Aliases (comma separated)</div>
              <input class="mt-1 w-full rounded-lg border border-ink-600/80 bg-ink-900/70 px-2 py-1" value={stringifyList(subject.aliases)} on:input={(e) => updateSubject(subjectIndex, { aliases: parseList(e.currentTarget.value) })} />
            </label>

            <div class="mt-4 rounded-lg border border-ink-600/80 bg-ink-900/50 p-3">
              <div class="flex items-center justify-between">
                <div class="text-xs uppercase tracking-[0.2em] text-mist-300">Bindings</div>
                <button class="text-xs text-accent-300" on:click={() => addBinding(subjectIndex)}>Add binding</button>
              </div>
              <div class="mt-2 space-y-2">
                {#if Object.entries(subject.bindings).length === 0}
                  <div class="text-xs text-mist-300">No bindings.</div>
                {/if}
                {#each Object.entries(subject.bindings) as [capability, providerId]}
                  <div class="grid grid-cols-[1fr_1fr_auto] gap-2 text-xs">
                    <select class="rounded-lg border border-ink-600/80 bg-ink-900/70 px-2 py-1" value={capability} on:change={(e) => {
                      const nextBindings = { ...subject.bindings };
                      delete nextBindings[capability];
                      nextBindings[e.currentTarget.value] = providerId;
                      updateSubject(subjectIndex, { bindings: nextBindings });
                    }}>
                      {#each capabilityOptions() as option}
                        <option value={option}>{option}</option>
                      {/each}
                    </select>
                    <select class="rounded-lg border border-ink-600/80 bg-ink-900/70 px-2 py-1" value={providerId} on:change={(e) => {
                      const nextBindings = { ...subject.bindings, [capability]: e.currentTarget.value };
                      updateSubject(subjectIndex, { bindings: nextBindings });
                    }}>
                      <option value="">Select provider</option>
                      {#each compatibleProviders(capability) as provider}
                        <option value={provider.id}>{provider.id}</option>
                      {/each}
                      {#if providerId && !compatibleProviders(capability).some((provider) => provider.id === providerId)}
                        <option value={providerId}>{providerId} (mismatch)</option>
                      {/if}
                    </select>
                    <button class="text-danger-400" on:click={() => removeBinding(subjectIndex, capability)}>Delete</button>
                  </div>
                {/each}
              </div>
              {#if missingCapabilities(subject).length > 0}
                <div class="mt-2 text-xs text-danger-400">
                  Missing capability bindings: {missingCapabilities(subject).join(', ')}
                </div>
              {/if}
            </div>

            <div class="mt-4 rounded-lg border border-ink-600/80 bg-ink-900/50 p-3">
              <div class="flex items-center justify-between">
                <div class="text-xs uppercase tracking-[0.2em] text-mist-300">Known failure modes</div>
                <button class="text-xs text-accent-300" on:click={() => addFailureMode(subjectIndex)}>Add mode</button>
              </div>
              <div class="mt-2 space-y-2">
                {#if subject.known_failure_modes.length === 0}
                  <div class="text-xs text-mist-300">No failure modes.</div>
                {/if}
                {#each subject.known_failure_modes as mode, modeIndex}
                  <div class="grid grid-cols-[1fr_1fr_auto] gap-2 text-xs">
                    <input class="rounded-lg border border-ink-600/80 bg-ink-900/70 px-2 py-1" value={mode.name} on:input={(e) => updateFailureMode(subjectIndex, modeIndex, { name: e.currentTarget.value })} />
                    <input class="rounded-lg border border-ink-600/80 bg-ink-900/70 px-2 py-1" value={stringifyList(mode.indicators)} on:input={(e) => updateFailureMode(subjectIndex, modeIndex, { indicators: parseList(e.currentTarget.value) })} />
                    <button class="text-danger-400" on:click={() => removeFailureMode(subjectIndex, modeIndex)}>Delete</button>
                  </div>
                {/each}
              </div>
            </div>
          </div>
        {/each}
      </div>
    </div>
  </div>

  <datalist id="binding-capabilities">
    {#each capabilityOptions() as capability}
      <option value={capability}></option>
    {/each}
  </datalist>

  <div class="surface p-6">
    <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Assistant transaction</div>
    <div class="mt-2 text-lg font-semibold">Proposed onboarding operations</div>
    <div class="mt-3 text-xs text-mist-300">{assistantStatus}</div>
    {#if assistantWarnings.length > 0}
      <div class="mt-3 space-y-1 text-xs text-danger-400">
        {#each assistantWarnings as warning}
          <div>• {warning}</div>
        {/each}
      </div>
    {/if}
    <div class="mt-4 grid gap-4 md:grid-cols-3 text-xs">
      <div>
        <div class="text-mist-300">Pending proposed ops</div>
        {#if assistantProposedOps.length === 0}
          <div class="mt-2 text-mist-400">None</div>
        {:else}
          <ul class="mt-2 space-y-1">
            {#each assistantProposedOps as op}
              <li class="rounded border border-ink-600/70 bg-ink-900/60 px-2 py-1">{op.type}</li>
            {/each}
          </ul>
          <div class="mt-2 flex gap-2">
            <button class="badge bg-accent-500/20 px-3 py-1 text-accent-200" on:click={onAssistantApplyPlanned}>Accept</button>
            <button class="badge bg-danger-500/20 px-3 py-1 text-danger-400" on:click={onAssistantRejectPlanned}>Reject</button>
          </div>
        {/if}
      </div>
      <div>
        <div class="text-mist-300">Applied ops</div>
        {#if assistantAppliedOps.length === 0}
          <div class="mt-2 text-mist-400">None</div>
        {:else}
          <ul class="mt-2 space-y-1">
            {#each assistantAppliedOps as op}
              <li class="rounded border border-ink-600/70 bg-ink-900/60 px-2 py-1">{op.type}</li>
            {/each}
          </ul>
        {/if}
      </div>
      <div>
        <div class="text-mist-300">Rejected ops</div>
        {#if assistantRejectedOps.length === 0}
          <div class="mt-2 text-mist-400">None</div>
        {:else}
          <ul class="mt-2 space-y-1">
            {#each assistantRejectedOps as op}
              <li class="rounded border border-ink-600/70 bg-ink-900/60 px-2 py-1">{op.type}</li>
            {/each}
          </ul>
        {/if}
      </div>
    </div>
  </div>

  <div class="grid gap-6 xl:grid-cols-3">
    <div class="surface p-6 xl:col-span-1">
      <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Resolved bindings</div>
      <div class="mt-2 text-lg font-semibold">Subject to provider mapping</div>
      {#if unusedProviderIds().length > 0}
        <div class="mt-2 text-xs text-danger-400">Unused providers: {unusedProviderIds().join(', ')}</div>
      {/if}
      <div class="mt-4 space-y-3 text-xs">
        {#if resolvedBindings.length === 0}
          <div class="text-mist-300">Run preview to compute resolved bindings.</div>
        {/if}
        {#each resolvedBindings as row}
          <div class="rounded-lg border border-ink-600/80 bg-ink-900/60 p-3">
            <div class="font-semibold text-mist-100">{row.subject} <span class="text-mist-300">({row.environment})</span></div>
            <div class="mt-2 space-y-1">
              {#if row.bindings.length === 0}
                <div class="text-mist-300">No bindings</div>
              {/if}
              {#each row.bindings as item}
                <div class={`flex items-center justify-between ${bindingStatus(item) === 'OK' ? 'text-accent-300' : 'text-danger-400'}`}>
                  <span>{item.capability} -> {item.provider_id}</span>
                  <span>{bindingStatus(item)}</span>
                </div>
              {/each}
            </div>
          </div>
        {/each}
      </div>
    </div>

    <div class="surface p-6 xl:col-span-1">
      <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Generated YAML</div>
      <div class="mt-2 text-lg font-semibold">Read-only output</div>
      <div class="mt-4 space-y-4 text-xs">
        <div>
          <div class="text-mist-300">catalog/instances.yaml</div>
          <pre class="mt-2 max-h-80 overflow-auto whitespace-pre-wrap rounded-lg border border-ink-700/80 bg-ink-900/70 p-3">{yamlPreview.catalog || 'Run preview to generate YAML.'}</pre>
        </div>
        <div>
          <div class="text-mist-300">kb/subjects.yaml</div>
          <pre class="mt-2 max-h-80 overflow-auto whitespace-pre-wrap rounded-lg border border-ink-700/80 bg-ink-900/70 p-3">{yamlPreview.kb || 'Run preview to generate YAML.'}</pre>
        </div>
      </div>
    </div>

    <div class="surface p-6 xl:col-span-1">
      <div class="text-xs uppercase tracking-[0.3em] text-mist-300">Diff preview</div>
      <div class="mt-2 text-lg font-semibold">File changes</div>
      <div class="mt-4 space-y-4 text-xs">
        <div>
          <div class="text-mist-300">catalog/instances.yaml</div>
          <pre class="mt-2 max-h-80 overflow-auto whitespace-pre-wrap rounded-lg border border-ink-700/80 bg-ink-900/70 p-3">{diffs.catalog || 'No diff yet.'}</pre>
        </div>
        <div>
          <div class="text-mist-300">kb/subjects.yaml</div>
          <pre class="mt-2 max-h-80 overflow-auto whitespace-pre-wrap rounded-lg border border-ink-700/80 bg-ink-900/70 p-3">{diffs.kb || 'No diff yet.'}</pre>
        </div>
      </div>
    </div>
  </div>

  <CopilotHost
    {model}
    {loading}
    onPreview={handlePreview}
    onApply={handleApply}
    onPlanIntent={onAssistantPlanIntent}
    onApplyPlanned={onAssistantApplyPlanned}
    onRejectPlanned={onAssistantRejectPlanned}
  />
</section>
