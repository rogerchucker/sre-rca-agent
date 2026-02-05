"use client";

import { useCoAgent } from "@copilotkit/react-core";

export interface RCAAgentState {
  // Incident info
  incident?: {
    title: string;
    severity: string;
    environment: string;
    subject: string;
    time_range: { start: string; end: string };
    labels: Record<string, string>;
    annotations: Record<string, string>;
  };
  // Knowledge base slice
  kb_slice?: {
    subject_cfg: Record<string, unknown>;
    providers: Record<string, unknown>;
  };
  // Evidence collected
  evidence?: Array<{
    id: string;
    kind: string;
    source: string;
    summary: string;
    time_range: { start: string; end: string };
    samples: string[];
    top_signals: Record<string, unknown>;
    pointers: Array<{ title?: string; url?: string }>;
    tags: string[];
  }>;
  // Generated hypotheses
  hypotheses?: Array<{
    id: string;
    statement: string;
    confidence: number;
    score_breakdown: Record<string, number>;
    supporting_evidence_ids: string[];
    contradictions: string[];
    validations: string[];
  }>;
  // Evidence collection plan
  plan?: Array<{
    tool: string;
    args: Record<string, unknown>;
  }>;
  // Current iteration
  iteration?: number;
  // Final report
  report?: {
    incident_summary: string;
    time_range: { start: string; end: string };
    top_hypothesis: {
      id: string;
      statement: string;
      confidence: number;
      score_breakdown: Record<string, number>;
      supporting_evidence_ids: string[];
      contradictions: string[];
      validations: string[];
    };
    other_hypotheses: Array<{
      id: string;
      statement: string;
      confidence: number;
    }>;
    evidence: Array<{ id: string; kind: string; summary: string }>;
    what_changed: Record<string, unknown>;
    impact_scope: Record<string, unknown>;
    next_validations: string[];
  };
  // Progress tracking
  current_step?: string;
  progress_message?: string;
  progress_percent?: number;
}

export function useRCAAgent() {
  return useCoAgent<RCAAgentState>({
    name: "rca-agent",
  });
}
