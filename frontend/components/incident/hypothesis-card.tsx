"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Target, CheckCircle, XCircle, Lightbulb } from "lucide-react";
import type { Hypothesis } from "@/lib/api";

interface HypothesisCardProps {
  hypothesis: Hypothesis;
  isTop?: boolean;
}

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.7) return "text-green-600";
  if (confidence >= 0.5) return "text-yellow-600";
  return "text-red-600";
}

function getConfidenceVariant(
  confidence: number
): "success" | "warning" | "secondary" {
  if (confidence >= 0.7) return "success";
  if (confidence >= 0.5) return "warning";
  return "secondary";
}

export function HypothesisCard({ hypothesis, isTop = false }: HypothesisCardProps) {
  const confidencePercent = Math.round(hypothesis.confidence * 100);

  return (
    <Card className={isTop ? "border-2 border-primary" : ""}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            {isTop && <Target className="h-5 w-5 text-primary" />}
            {isTop ? "Top Hypothesis" : `Hypothesis ${hypothesis.id}`}
          </CardTitle>
          <Badge variant={getConfidenceVariant(hypothesis.confidence)}>
            {confidencePercent}% confidence
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="font-medium">{hypothesis.statement}</p>

        <div className="space-y-1">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Confidence</span>
            <span className={getConfidenceColor(hypothesis.confidence)}>
              {confidencePercent}%
            </span>
          </div>
          <Progress value={confidencePercent} className="h-2" />
        </div>

        {hypothesis.score_breakdown &&
          Object.keys(hypothesis.score_breakdown).length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium">Score Breakdown</p>
              <div className="grid grid-cols-2 gap-2 text-sm">
                {Object.entries(hypothesis.score_breakdown).map(([key, value]) => (
                  <div
                    key={key}
                    className="flex justify-between rounded bg-muted p-2"
                  >
                    <span className="text-muted-foreground capitalize">
                      {key.replace(/_/g, " ")}
                    </span>
                    <span>{typeof value === "number" ? value.toFixed(2) : value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

        {hypothesis.supporting_evidence_ids &&
          hypothesis.supporting_evidence_ids.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium flex items-center gap-1">
                <CheckCircle className="h-4 w-4 text-green-600" />
                Supporting Evidence
              </p>
              <div className="flex flex-wrap gap-1">
                {hypothesis.supporting_evidence_ids.map((id) => (
                  <Badge key={id} variant="outline" className="text-xs">
                    {id}
                  </Badge>
                ))}
              </div>
            </div>
          )}

        {hypothesis.contradictions && hypothesis.contradictions.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-medium flex items-center gap-1">
              <XCircle className="h-4 w-4 text-red-600" />
              Contradictions
            </p>
            <ul className="text-sm text-muted-foreground list-disc list-inside">
              {hypothesis.contradictions.map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ul>
          </div>
        )}

        {hypothesis.validations && hypothesis.validations.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-medium flex items-center gap-1">
              <Lightbulb className="h-4 w-4 text-yellow-600" />
              Next Validations
            </p>
            <ul className="text-sm text-muted-foreground list-disc list-inside">
              {hypothesis.validations.map((v, i) => (
                <li key={i}>{v}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface HypothesesListProps {
  hypotheses: Hypothesis[];
}

export function HypothesesList({ hypotheses }: HypothesesListProps) {
  if (hypotheses.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Hypotheses</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No hypotheses generated yet.
          </p>
        </CardContent>
      </Card>
    );
  }

  const sorted = [...hypotheses].sort((a, b) => b.confidence - a.confidence);
  const top = sorted[0];
  const others = sorted.slice(1);

  return (
    <div className="space-y-4">
      <HypothesisCard hypothesis={top} isTop />
      {others.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Other Hypotheses</CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[300px]">
              <div className="space-y-3">
                {others.map((h) => (
                  <div key={h.id} className="rounded-lg border p-3 space-y-2">
                    <div className="flex items-start justify-between">
                      <p className="text-sm font-medium">{h.statement}</p>
                      <Badge variant={getConfidenceVariant(h.confidence)}>
                        {Math.round(h.confidence * 100)}%
                      </Badge>
                    </div>
                    {h.validations && h.validations.length > 0 && (
                      <p className="text-xs text-muted-foreground">
                        Validate: {h.validations[0]}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
