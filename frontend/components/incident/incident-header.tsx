"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Clock, MapPin, RefreshCw } from "lucide-react";
import Link from "next/link";
import type { Incident } from "@/lib/api";

interface IncidentHeaderProps {
  incident: Incident;
  onRefresh?: () => void;
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

export function IncidentHeader({ incident, onRefresh }: IncidentHeaderProps) {
  const startTime = incident.starts_at || incident.time_range?.start;
  const endTime = incident.ends_at || incident.time_range?.end;

  return (
    <div className="border-b pb-4 mb-4">
      <div className="flex items-center gap-2 mb-2">
        <Button variant="ghost" size="sm" asChild>
          <Link href="/incident">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back
          </Link>
        </Button>
        {onRefresh && (
          <Button variant="ghost" size="sm" onClick={onRefresh}>
            <RefreshCw className="h-4 w-4 mr-1" />
            Refresh
          </Button>
        )}
      </div>
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Badge variant={getSeverityVariant(incident.severity)}>
              {incident.severity}
            </Badge>
            <Badge variant="outline">{incident.environment}</Badge>
            {incident.subject && (
              <Badge variant="secondary">{incident.subject}</Badge>
            )}
            {incident.status && (
              <Badge variant="secondary">{incident.status}</Badge>
            )}
          </div>
          <h1 className="text-2xl font-bold">{incident.title}</h1>
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <span className="flex items-center gap-1">
              <MapPin className="h-4 w-4" />
              {incident.id}
            </span>
            {startTime && (
              <span className="flex items-center gap-1">
                <Clock className="h-4 w-4" />
                {new Date(startTime).toLocaleString()} -{" "}
                {endTime ? new Date(endTime).toLocaleString() : "ongoing"}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
