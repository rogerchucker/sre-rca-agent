"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ArrowRight } from "lucide-react";
import type { Incident } from "@/lib/api";

interface IncidentListProps {
  incidents: Incident[];
  title?: string;
}

function getSeverityVariant(
  severity: string
): "destructive" | "warning" | "secondary" {
  switch (severity.toLowerCase()) {
    case "p1":
    case "critical":
      return "destructive";
    case "p2":
    case "high":
      return "warning";
    default:
      return "secondary";
  }
}

function getStatusVariant(
  status?: string
): "default" | "secondary" | "success" | "warning" {
  switch (status?.toLowerCase()) {
    case "investigation":
    case "investigating":
      return "warning";
    case "resolved":
    case "steady_state":
      return "success";
    case "review":
      return "default";
    default:
      return "secondary";
  }
}

export function IncidentList({ incidents, title = "Recent Incidents" }: IncidentListProps) {
  if (incidents.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No incidents found.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>{title}</CardTitle>
        <Button variant="outline" size="sm" asChild>
          <Link href="/incident">View All</Link>
        </Button>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {incidents.map((incident) => (
            <div
              key={incident.id}
              className="flex items-center justify-between border-b pb-4 last:border-0 last:pb-0"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Badge variant={getSeverityVariant(incident.severity)}>
                    {incident.severity}
                  </Badge>
                  <Badge variant="outline">{incident.environment}</Badge>
                  {incident.status && (
                    <Badge variant={getStatusVariant(incident.status)}>
                      {incident.status}
                    </Badge>
                  )}
                </div>
                <p className="font-medium">{incident.title}</p>
                <p className="text-xs text-muted-foreground">
                  {incident.updated || incident.updated_at || ""}
                </p>
              </div>
              <Button variant="ghost" size="sm" asChild>
                <Link href={`/incident/${incident.id}`}>
                  Investigate
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
