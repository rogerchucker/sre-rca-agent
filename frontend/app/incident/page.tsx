"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ArrowRight, Search, RefreshCw } from "lucide-react";
import { getIncidents, queryIncidents } from "@/lib/api";
import type { Incident } from "@/lib/api";

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

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");

  const loadIncidents = async () => {
    setLoading(true);
    try {
      // Try to get incidents from the query endpoint first
      try {
        const result = await queryIncidents({ page: 1, page_size: 50 });
        if (result.items.length > 0) {
          setIncidents(result.items);
          return;
        }
      } catch {
        // Fall back to UI incidents endpoint
      }
      const data = await getIncidents();
      setIncidents(data);
    } catch (error) {
      console.error("Failed to load incidents:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIncidents();
  }, []);

  const filteredIncidents = incidents.filter(
    (incident) =>
      incident.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      incident.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      incident.subject?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Incidents</h1>
          <p className="text-muted-foreground">
            View and investigate all incidents
          </p>
        </div>
        <Button variant="outline" onClick={loadIncidents} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search incidents..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-9"
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            All Incidents
            <Badge variant="secondary">{filteredIncidents.length}</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-muted-foreground">
              Loading incidents...
            </div>
          ) : filteredIncidents.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No incidents found.
            </div>
          ) : (
            <ScrollArea className="h-[600px]">
              <div className="space-y-4">
                {filteredIncidents.map((incident) => (
                  <div
                    key={incident.id}
                    className="flex items-center justify-between border rounded-lg p-4 hover:bg-accent/50 transition-colors"
                  >
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
                          <Badge variant={getStatusVariant(incident.status)}>
                            {incident.status}
                          </Badge>
                        )}
                      </div>
                      <p className="font-medium">{incident.title}</p>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span>ID: {incident.id}</span>
                        {incident.updated && <span>Updated {incident.updated}</span>}
                        {incident.created_at && (
                          <span>
                            Created {new Date(incident.created_at).toLocaleString()}
                          </span>
                        )}
                      </div>
                    </div>
                    <Button variant="outline" asChild>
                      <Link href={`/incident/${incident.id}`}>
                        Investigate
                        <ArrowRight className="ml-2 h-4 w-4" />
                      </Link>
                    </Button>
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

