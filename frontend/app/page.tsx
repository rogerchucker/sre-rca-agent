"use client";

import { useEffect, useState } from "react";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { AttentionQueue } from "@/components/dashboard/attention-queue";
import { IncidentList } from "@/components/dashboard/incident-list";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { getIncidents, getAttentionQueue, getSummary, getMode } from "@/lib/api";
import type { Incident } from "@/lib/api";

export default function DashboardPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [attention, setAttention] = useState<
    Array<{
      id: string;
      title: string;
      severity: string;
      environment: string;
      updated_at: string;
    }>
  >([]);
  const [summary, setSummary] = useState<{
    summary: string;
    confidence: number | null;
    citations: string[];
  } | null>(null);
  const [liveMode, setLiveMode] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [incidentsData, attentionData, summaryData, modeData] =
          await Promise.all([
            getIncidents(),
            getAttentionQueue(),
            getSummary(),
            getMode(),
          ]);
        setIncidents(incidentsData);
        setAttention(attentionData);
        setSummary(summaryData);
        setLiveMode(modeData.live_mode);
      } catch (error) {
        console.error("Failed to load dashboard data:", error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-muted-foreground">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">RCA Agent Dashboard</h1>
          <p className="text-muted-foreground">
            AI-powered Root Cause Analysis for Incident Investigation
          </p>
        </div>
        <Badge variant={liveMode ? "default" : "secondary"}>
          {liveMode ? "Live Mode" : "Demo Mode"}
        </Badge>
      </div>

      <StatsCards />

      <div className="grid gap-6 lg:grid-cols-2">
        <AttentionQueue items={attention} />

        {summary && (
          <Card>
            <CardHeader>
              <CardTitle>Latest RCA Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm">{summary.summary}</p>
              {summary.confidence !== null && (
                <div className="flex items-center gap-2">
                  <span className="text-sm text-muted-foreground">
                    Confidence:
                  </span>
                  <Badge
                    variant={
                      summary.confidence >= 0.7
                        ? "success"
                        : summary.confidence >= 0.5
                        ? "warning"
                        : "secondary"
                    }
                  >
                    {Math.round(summary.confidence * 100)}%
                  </Badge>
                </div>
              )}
              {summary.citations.length > 0 && (
                <div>
                  <span className="text-sm text-muted-foreground">
                    Supporting evidence:
                  </span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {summary.citations.map((c) => (
                      <Badge key={c} variant="outline" className="text-xs">
                        {c}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>

      <IncidentList incidents={incidents} />
    </div>
  );
}
