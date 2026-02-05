"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { BookOpen, AlertTriangle, History, Settings } from "lucide-react";
import {
  getRunbooks,
  getPatterns,
  getHistoricalIncidents,
  getOnboardingConfig,
  type Runbook,
  type Pattern,
  type Incident,
} from "@/lib/api";

export default function KnowledgePage() {
  const [runbooks, setRunbooks] = useState<Runbook[]>([]);
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [onboarding, setOnboarding] = useState<{
    subjects: unknown[];
    providers: Array<{
      id: string;
      category: string;
      type: string;
      capabilities: Record<string, unknown>;
    }>;
  } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [runbooksData, patternsData, incidentsData, onboardingData] =
          await Promise.all([
            getRunbooks(),
            getPatterns(),
            getHistoricalIncidents(),
            getOnboardingConfig(),
          ]);
        setRunbooks(runbooksData);
        setPatterns(patternsData);
        setIncidents(incidentsData);
        setOnboarding(onboardingData);
      } catch (error) {
        console.error("Failed to load knowledge data:", error);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-muted-foreground">Loading knowledge base...</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Knowledge Base</h1>
        <p className="text-muted-foreground">
          Runbooks, patterns, and historical incident data
        </p>
      </div>

      <Tabs defaultValue="runbooks" className="space-y-4">
        <TabsList>
          <TabsTrigger value="runbooks" className="flex items-center gap-2">
            <BookOpen className="h-4 w-4" />
            Runbooks ({runbooks.length})
          </TabsTrigger>
          <TabsTrigger value="patterns" className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" />
            Patterns ({patterns.length})
          </TabsTrigger>
          <TabsTrigger value="incidents" className="flex items-center gap-2">
            <History className="h-4 w-4" />
            Historical ({incidents.length})
          </TabsTrigger>
          <TabsTrigger value="config" className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            Configuration
          </TabsTrigger>
        </TabsList>

        <TabsContent value="runbooks">
          <Card>
            <CardHeader>
              <CardTitle>Runbooks</CardTitle>
            </CardHeader>
            <CardContent>
              {runbooks.length === 0 ? (
                <p className="text-muted-foreground">No runbooks configured.</p>
              ) : (
                <ScrollArea className="h-[500px]">
                  <div className="space-y-4">
                    {runbooks.map((runbook, index) => (
                      <div
                        key={index}
                        className="border rounded-lg p-4 space-y-2"
                      >
                        <div className="flex items-center gap-2">
                          <BookOpen className="h-4 w-4 text-muted-foreground" />
                          <span className="font-medium">{runbook.name}</span>
                          <Badge variant="secondary">{runbook.subject}</Badge>
                        </div>
                        {runbook.indicators.length > 0 && (
                          <div className="ml-6">
                            <p className="text-sm text-muted-foreground mb-1">
                              Indicators:
                            </p>
                            <div className="flex flex-wrap gap-1">
                              {runbook.indicators.map((indicator, i) => (
                                <Badge
                                  key={i}
                                  variant="outline"
                                  className="text-xs"
                                >
                                  {indicator}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="patterns">
          <Card>
            <CardHeader>
              <CardTitle>Known Failure Patterns</CardTitle>
            </CardHeader>
            <CardContent>
              {patterns.length === 0 ? (
                <p className="text-muted-foreground">
                  No failure patterns configured.
                </p>
              ) : (
                <ScrollArea className="h-[500px]">
                  <div className="space-y-4">
                    {patterns.map((pattern, index) => (
                      <div
                        key={index}
                        className="border rounded-lg p-4 space-y-2"
                      >
                        <div className="flex items-center gap-2">
                          <AlertTriangle className="h-4 w-4 text-yellow-500" />
                          <span className="font-medium">{pattern.pattern}</span>
                          <Badge variant="secondary">{pattern.subject}</Badge>
                        </div>
                        {pattern.indicators.length > 0 && (
                          <div className="ml-6">
                            <p className="text-sm text-muted-foreground mb-1">
                              Indicators:
                            </p>
                            <div className="flex flex-wrap gap-1">
                              {pattern.indicators.map((indicator, i) => (
                                <Badge
                                  key={i}
                                  variant="outline"
                                  className="text-xs"
                                >
                                  {indicator}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="incidents">
          <Card>
            <CardHeader>
              <CardTitle>Historical Incidents</CardTitle>
            </CardHeader>
            <CardContent>
              {incidents.length === 0 ? (
                <p className="text-muted-foreground">
                  No historical incidents recorded.
                </p>
              ) : (
                <ScrollArea className="h-[500px]">
                  <div className="space-y-4">
                    {incidents.map((incident) => (
                      <div
                        key={incident.id}
                        className="border rounded-lg p-4 space-y-2"
                      >
                        <div className="flex items-center gap-2">
                          <Badge
                            variant={
                              incident.severity.toLowerCase() === "p1"
                                ? "destructive"
                                : incident.severity.toLowerCase() === "p2"
                                ? "warning"
                                : "secondary"
                            }
                          >
                            {incident.severity}
                          </Badge>
                          <Badge variant="outline">{incident.environment}</Badge>
                          {incident.subject && (
                            <Badge variant="secondary">{incident.subject}</Badge>
                          )}
                        </div>
                        <p className="font-medium">{incident.title}</p>
                        <p className="text-xs text-muted-foreground">
                          {incident.created_at &&
                            new Date(incident.created_at).toLocaleString()}
                        </p>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="config">
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Subjects</CardTitle>
              </CardHeader>
              <CardContent>
                {onboarding?.subjects.length === 0 ? (
                  <p className="text-muted-foreground">
                    No subjects configured.
                  </p>
                ) : (
                  <ScrollArea className="h-[300px]">
                    <div className="space-y-2">
                      {onboarding?.subjects.map((subject: unknown, index: number) => {
                        const s = subject as { name?: string; environment?: string };
                        return (
                          <div
                            key={index}
                            className="border rounded-lg p-3"
                          >
                            <p className="font-medium">{s.name || `Subject ${index + 1}`}</p>
                            {s.environment && (
                              <Badge variant="outline" className="mt-1">
                                {s.environment}
                              </Badge>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </ScrollArea>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Providers</CardTitle>
              </CardHeader>
              <CardContent>
                {onboarding?.providers.length === 0 ? (
                  <p className="text-muted-foreground">
                    No providers configured.
                  </p>
                ) : (
                  <ScrollArea className="h-[300px]">
                    <div className="space-y-2">
                      {onboarding?.providers.map((provider) => (
                        <div
                          key={provider.id}
                          className="border rounded-lg p-3 space-y-1"
                        >
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{provider.id}</span>
                            <Badge variant="secondary">{provider.category}</Badge>
                          </div>
                          <p className="text-sm text-muted-foreground">
                            Type: {provider.type}
                          </p>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
