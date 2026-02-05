"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { IncidentHeader } from "@/components/incident/incident-header";
import { EvidenceList } from "@/components/incident/evidence-list";
import { HypothesesList } from "@/components/incident/hypothesis-card";
import { Timeline } from "@/components/incident/timeline";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useRCAAgent } from "@/hooks/use-rca-agent";
import {
  getIncident,
  getIncidentTimeline,
  getIncidentHypotheses,
  getLatestReport,
  type Incident,
  type TimelineItem,
  type Hypothesis,
  type EvidenceItem,
  type RCAReport,
} from "@/lib/api";

export default function IncidentDetailPage() {
  const params = useParams();
  const incidentId = params.id as string;

  const [incident, setIncident] = useState<Incident | null>(null);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [hypotheses, setHypotheses] = useState<Hypothesis[]>([]);
  const [report, setReport] = useState<RCAReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { state: agentState } = useRCAAgent();

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      // Try to get incident from the API
      try {
        const inc = await getIncident(incidentId);
        setIncident(inc);
      } catch {
        // Create a placeholder incident for demo mode
        setIncident({
          id: incidentId,
          title: "Loading...",
          severity: "P1",
          environment: "prod",
        });
      }

      // Load timeline and hypotheses
      const [timelineData, hypothesesData] = await Promise.all([
        getIncidentTimeline(incidentId),
        getIncidentHypotheses(incidentId),
      ]);
      setTimeline(timelineData);
      setHypotheses(hypothesesData);

      // Try to load the latest report
      try {
        const reportData = await getLatestReport(incidentId);
        setReport(reportData);
        // Update incident with report data if available
        if (reportData.incident_summary) {
          setIncident((prev) =>
            prev
              ? { ...prev, title: reportData.incident_summary.split(" (")[0] }
              : prev
          );
        }
      } catch {
        // Report might not exist yet
      }
    } catch (err) {
      console.error("Failed to load incident data:", err);
      setError("Failed to load incident data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [incidentId]);

  // Update data from agent state if available
  useEffect(() => {
    if (agentState?.report) {
      const r = agentState.report;
      setReport({
        incident_summary: r.incident_summary,
        time_range: r.time_range,
        top_hypothesis: r.top_hypothesis,
        other_hypotheses: r.other_hypotheses,
        evidence: r.evidence.map((e) => ({
          id: e.id,
          kind: e.kind,
          source: "",
          summary: e.summary,
          time_range: { start: "", end: "" },
        })),
        next_validations: r.next_validations,
        what_changed: r.what_changed,
        impact_scope: r.impact_scope,
      } as RCAReport);
    }
    if (agentState?.evidence) {
      const timelineItems: TimelineItem[] = agentState.evidence.map((e) => ({
        time: e.time_range?.start || "",
        label: e.summary,
        source: e.source,
        kind: e.kind,
      }));
      setTimeline(timelineItems);
    }
    if (agentState?.hypotheses) {
      setHypotheses(
        agentState.hypotheses.map((h) => ({
          id: h.id,
          statement: h.statement,
          confidence: h.confidence,
          score_breakdown: h.score_breakdown,
          supporting_evidence_ids: h.supporting_evidence_ids,
          contradictions: h.contradictions,
          validations: h.validations,
        }))
      );
    }
  }, [agentState]);

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-muted-foreground">Loading incident details...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="py-8">
            <p className="text-center text-destructive">{error}</p>
            <Button onClick={loadData} className="mt-4 mx-auto block">
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!incident) {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="py-8">
            <p className="text-center text-muted-foreground">
              Incident not found
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const evidence: EvidenceItem[] = report?.evidence || [];

  return (
    <div className="p-6 space-y-6">
      <IncidentHeader incident={incident} onRefresh={loadData} />

      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="evidence">
            Evidence {evidence.length > 0 && `(${evidence.length})`}
          </TabsTrigger>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
          <TabsTrigger value="hypotheses">Hypotheses</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid gap-4 lg:grid-cols-2">
            {/* Summary Card */}
            <Card>
              <CardHeader>
                <CardTitle>RCA Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {report ? (
                  <>
                    <p>{report.incident_summary}</p>
                    {report.top_hypothesis && (
                      <div className="space-y-2 pt-4 border-t">
                        <div className="flex items-center justify-between">
                          <span className="font-medium">Top Hypothesis</span>
                          <Badge
                            variant={
                              report.top_hypothesis.confidence >= 0.7
                                ? "success"
                                : report.top_hypothesis.confidence >= 0.5
                                ? "warning"
                                : "secondary"
                            }
                          >
                            {Math.round(report.top_hypothesis.confidence * 100)}%
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {report.top_hypothesis.statement}
                        </p>
                      </div>
                    )}
                    {report.next_validations && report.next_validations.length > 0 && (
                      <div className="space-y-2 pt-4 border-t">
                        <span className="font-medium">Next Steps</span>
                        <ul className="text-sm text-muted-foreground list-disc list-inside">
                          {report.next_validations.slice(0, 3).map((v, i) => (
                            <li key={i}>{v}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </>
                ) : (
                  <p className="text-muted-foreground">
                    No RCA report available yet. Start an investigation using the
                    chat assistant.
                  </p>
                )}
              </CardContent>
            </Card>

            {/* What Changed Card */}
            {report?.what_changed && (
              <Card>
                <CardHeader>
                  <CardTitle>What Changed</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {Object.entries(report.what_changed).map(([key, value]) => (
                    <div key={key}>
                      <span className="text-sm font-medium capitalize">
                        {key.replace(/_/g, " ")}
                      </span>
                      {Array.isArray(value) && value.length > 0 ? (
                        <div className="mt-1 space-y-1">
                          {value.slice(0, 3).map((item: unknown, i: number) => (
                            <div
                              key={i}
                              className="text-xs text-muted-foreground bg-muted p-2 rounded"
                            >
                              {typeof item === "object"
                                ? JSON.stringify(item, null, 2)
                                : String(item)}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs text-muted-foreground">None</p>
                      )}
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}
          </div>

          {/* Quick timeline view */}
          <Timeline items={timeline.slice(0, 10)} />
        </TabsContent>

        <TabsContent value="evidence">
          <EvidenceList evidence={evidence} />
        </TabsContent>

        <TabsContent value="timeline">
          <Timeline items={timeline} />
        </TabsContent>

        <TabsContent value="hypotheses">
          <HypothesesList hypotheses={hypotheses} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
