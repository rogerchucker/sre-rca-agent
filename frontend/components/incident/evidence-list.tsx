"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  FileText,
  AlertTriangle,
  Activity,
  GitCommit,
  Rocket,
  Cpu,
  Database,
  Network,
  BookOpen,
} from "lucide-react";
import type { EvidenceItem } from "@/lib/api";

interface EvidenceListProps {
  evidence: EvidenceItem[];
}

const kindIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  log: FileText,
  alert: AlertTriangle,
  metric: Activity,
  change: GitCommit,
  deployment: Rocket,
  build: Cpu,
  event: Database,
  trace: Network,
  service_graph: Network,
  runbook: BookOpen,
};

function getKindColor(kind: string): string {
  switch (kind) {
    case "alert":
      return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100";
    case "log":
      return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100";
    case "metric":
      return "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100";
    case "deployment":
      return "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-100";
    case "change":
      return "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-100";
    case "build":
      return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100";
    case "event":
      return "bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-100";
    case "trace":
      return "bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-100";
    default:
      return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-100";
  }
}

export function EvidenceList({ evidence }: EvidenceListProps) {
  if (evidence.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Evidence</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No evidence collected yet.
          </p>
        </CardContent>
      </Card>
    );
  }

  // Group evidence by kind
  const grouped = evidence.reduce((acc, item) => {
    const kind = item.kind || "other";
    if (!acc[kind]) acc[kind] = [];
    acc[kind].push(item);
    return acc;
  }, {} as Record<string, EvidenceItem[]>);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Evidence
          <Badge variant="secondary">{evidence.length} items</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[400px]">
          <div className="space-y-6">
            {Object.entries(grouped).map(([kind, items]) => {
              const Icon = kindIcons[kind] || FileText;
              return (
                <div key={kind}>
                  <div className="flex items-center gap-2 mb-2">
                    <Icon className="h-4 w-4" />
                    <span className="font-medium capitalize">{kind}</span>
                    <Badge variant="outline" className="text-xs">
                      {items.length}
                    </Badge>
                  </div>
                  <div className="space-y-2 ml-6">
                    {items.map((item) => (
                      <div
                        key={item.id}
                        className="rounded-lg border p-3 space-y-2"
                      >
                        <div className="flex items-start justify-between">
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <Badge className={getKindColor(item.kind)}>
                                {item.kind}
                              </Badge>
                              <span className="text-xs text-muted-foreground">
                                {item.source}
                              </span>
                            </div>
                            <p className="text-sm">{item.summary}</p>
                          </div>
                        </div>
                        {item.samples && item.samples.length > 0 && (
                          <div className="rounded bg-muted p-2">
                            <p className="text-xs font-mono text-muted-foreground line-clamp-3">
                              {item.samples[0]}
                            </p>
                          </div>
                        )}
                        {item.pointers && item.pointers.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {item.pointers.map((p, i) => (
                              <a
                                key={i}
                                href={p.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs text-blue-600 hover:underline"
                              >
                                {p.title || "Link"}
                              </a>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
