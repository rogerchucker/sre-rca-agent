"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Progress } from "@/components/ui/progress";
import { Timeline } from "@/components/incident/timeline";
import { Activity, TrendingUp } from "lucide-react";
import { getSignalsTimeline, getSignalsCorrelation, type TimelineItem } from "@/lib/api";

export default function SignalsPage() {
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [correlation, setCorrelation] = useState<
    Array<{ pair: string; score: number }>
  >([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [timelineData, correlationData] = await Promise.all([
          getSignalsTimeline(),
          getSignalsCorrelation(),
        ]);
        setTimeline(timelineData);
        setCorrelation(correlationData.pairs || []);
      } catch (error) {
        console.error("Failed to load signals data:", error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-muted-foreground">Loading signals data...</div>
      </div>
    );
  }

  // Group timeline items by kind for summary
  const kindCounts = timeline.reduce((acc, item) => {
    const kind = item.kind || "unknown";
    acc[kind] = (acc[kind] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Signals</h1>
        <p className="text-muted-foreground">
          Evidence correlation and signal timeline
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Signal Type Summary */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Signal Types
            </CardTitle>
          </CardHeader>
          <CardContent>
            {Object.keys(kindCounts).length === 0 ? (
              <p className="text-muted-foreground">No signals recorded.</p>
            ) : (
              <div className="space-y-3">
                {Object.entries(kindCounts)
                  .sort(([, a], [, b]) => b - a)
                  .map(([kind, count]) => (
                    <div key={kind} className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium capitalize">
                          {kind}
                        </span>
                        <Badge variant="secondary">{count}</Badge>
                      </div>
                      <Progress
                        value={(count / timeline.length) * 100}
                        className="h-2"
                      />
                    </div>
                  ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Correlation Scores */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Correlation Scores
            </CardTitle>
          </CardHeader>
          <CardContent>
            {correlation.length === 0 ? (
              <p className="text-muted-foreground">
                No correlations calculated.
              </p>
            ) : (
              <ScrollArea className="h-[200px]">
                <div className="space-y-3">
                  {correlation
                    .sort((a, b) => b.score - a.score)
                    .map((item, index) => (
                      <div key={index} className="space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium">{item.pair}</span>
                          <Badge
                            variant={
                              item.score >= 0.7
                                ? "success"
                                : item.score >= 0.4
                                ? "warning"
                                : "secondary"
                            }
                          >
                            {(item.score * 100).toFixed(0)}%
                          </Badge>
                        </div>
                        <Progress value={item.score * 100} className="h-2" />
                      </div>
                    ))}
                </div>
              </ScrollArea>
            )}
          </CardContent>
        </Card>

        {/* Summary Stats */}
        <Card>
          <CardHeader>
            <CardTitle>Summary</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                Total Signals
              </span>
              <span className="text-2xl font-bold">{timeline.length}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">Signal Types</span>
              <span className="text-2xl font-bold">
                {Object.keys(kindCounts).length}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                Correlation Pairs
              </span>
              <span className="text-2xl font-bold">{correlation.length}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Full Timeline */}
      <Timeline items={timeline} />
    </div>
  );
}
