"use client";

import { CopilotKit } from "@copilotkit/react-core";
import { CopilotSidebar } from "@copilotkit/react-ui";

interface CopilotProviderProps {
  children: React.ReactNode;
}

export function CopilotProvider({ children }: CopilotProviderProps) {
  return (
    <CopilotKit runtimeUrl="/api/copilotkit" agent="rca-agent">
      {children}
      <CopilotSidebar
        defaultOpen={false}
        labels={{
          title: "RCA Investigation Assistant",
          initial:
            "Hi! I can help you investigate incidents. Try asking me to analyze an incident or explain the evidence.",
        }}
      />
    </CopilotKit>
  );
}
