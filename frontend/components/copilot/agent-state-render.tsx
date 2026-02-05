"use client";

import { useCoAgentStateRender } from "@copilotkit/react-core";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CheckCircle, Loader2, AlertCircle } from "lucide-react";
import type { RCAAgentState } from "@/hooks/use-rca-agent";

const stepLabels: Record<string, string> = {
  normalize_incident: "Parsing Incident",
  load_kb_slice: "Loading Knowledge Base",
  seed_alert_evidence: "Capturing Alert",
  plan_evidence: "Planning Evidence Collection",
  collect_evidence: "Collecting Evidence",
  summarize_evidence: "Summarizing Evidence",
  hypothesize: "Generating Hypotheses",
  score_and_report: "Scoring & Reporting",
  complete: "Complete",
};

export function AgentStateRenderer() {
  useCoAgentStateRender<RCAAgentState>({
    name: "rca-agent",
    render: ({ state, status }) => {
      if (!state) return null;

      const currentStep = state.current_step || "";
      const progressMessage = state.progress_message || "";
      const progressPercent = state.progress_percent || 0;
      const isRunning = status === "inProgress";
      const isComplete = currentStep === "complete";

      return (
        <Card className="my-2 border-l-4 border-l-primary">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-3">
              {isRunning ? (
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
              ) : isComplete ? (
                <CheckCircle className="h-4 w-4 text-green-500" />
              ) : (
                <AlertCircle className="h-4 w-4 text-muted-foreground" />
              )}
              <span className="font-medium">
                {stepLabels[currentStep] || currentStep || "Initializing..."}
              </span>
              <Badge
                variant={isComplete ? "success" : isRunning ? "default" : "secondary"}
                className="ml-auto"
              >
                {progressPercent}%
              </Badge>
            </div>
            <Progress value={progressPercent} className="h-2 mb-2" />
            <p className="text-sm text-muted-foreground">{progressMessage}</p>

            {state.evidence && state.evidence.length > 0 && (
              <div className="mt-3 pt-3 border-t">
                <p className="text-xs text-muted-foreground mb-1">
                  Evidence collected: {state.evidence.length} items
                </p>
                <div className="flex flex-wrap gap-1">
                  {Array.from(new Set(state.evidence.map((e) => e.kind))).map(
                    (kind) => (
                      <Badge key={kind} variant="outline" className="text-xs">
                        {kind}
                      </Badge>
                    )
                  )}
                </div>
              </div>
            )}

            {state.report?.top_hypothesis && (
              <div className="mt-3 pt-3 border-t">
                <p className="text-xs font-medium mb-1">Top Hypothesis</p>
                <p className="text-sm">{state.report.top_hypothesis.statement}</p>
                <Badge
                  variant={
                    state.report.top_hypothesis.confidence >= 0.7
                      ? "success"
                      : state.report.top_hypothesis.confidence >= 0.5
                      ? "warning"
                      : "secondary"
                  }
                  className="mt-1"
                >
                  {(state.report.top_hypothesis.confidence * 100).toFixed(0)}%
                  confidence
                </Badge>
              </div>
            )}
          </CardContent>
        </Card>
      );
    },
  });

  return null;
}
