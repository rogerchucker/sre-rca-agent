import React from 'react';
import { CopilotKit, useCopilotAction, useCopilotReadable } from '@copilotkit/react-core';
import { CopilotPopup } from '@copilotkit/react-ui';
import type { OnboardingModel } from '$lib/api';

type OnboardingCopilotProps = {
  model: OnboardingModel;
  loading: boolean;
  onPreview: () => Promise<void>;
  onApply: () => Promise<void>;
  onPlanIntent: (intent: string) => Promise<string>;
  onApplyPlanned: () => Promise<string>;
  onRejectPlanned: () => string;
};

function OnboardingCopilotActions(props: OnboardingCopilotProps) {
  useCopilotReadable(
    {
      description:
        'Current onboarding state. providers are available integration instances. subjects are service definitions with bindings to providers.',
      value: props.model
    },
    [props.model]
  );

  useCopilotAction({
    name: 'plan_onboarding_changes',
    description: 'Create a proposed onboarding operation plan from natural language intent.',
    parameters: [
      { name: 'intent', type: 'string', required: true }
    ],
    handler: async ({ intent }: any) => {
      return await props.onPlanIntent(intent);
    }
  });

  useCopilotAction({
    name: 'apply_planned_changes',
    description: 'Apply the currently proposed onboarding operations to the form model.',
    handler: async () => {
      return await props.onApplyPlanned();
    }
  });

  useCopilotAction({
    name: 'reject_planned_changes',
    description: 'Discard the currently proposed onboarding operations.',
    handler: () => {
      return props.onRejectPlanned();
    }
  });

  useCopilotAction({
    name: 'preview_onboarding_changes',
    description: 'Run preview and validation for current onboarding model.',
    handler: async () => {
      await props.onPreview();
      return 'Preview completed. Check validation errors and diff panels.';
    }
  });

  useCopilotAction({
    name: 'apply_onboarding_changes',
    description: 'Apply current onboarding model to YAML files after validation.',
    handler: async () => {
      await props.onApply();
      return 'Apply requested. Backups are created automatically by the backend endpoint.';
    }
  });

  return null;
}

export function OnboardingCopilot(props: OnboardingCopilotProps) {
  return (
    <CopilotKit runtimeUrl="/copilotkit" useSingleEndpoint={true} showDevConsole={false} enableInspector={false}>
      <OnboardingCopilotActions {...props} />
      <CopilotPopup
        instructions="You are an SRE onboarding assistant. Use plan_onboarding_changes first, then apply_planned_changes only after user confirmation. Never invent provider ids and always keep capability-to-category matches."
        labels={{
          title: 'Onboarding Assistant',
          initial: 'I can propose onboarding operations and apply them on confirmation.'
        }}
        defaultOpen={false}
      />
    </CopilotKit>
  );
}
