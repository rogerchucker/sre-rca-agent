"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Play,
  CheckCircle,
  AlertTriangle,
  ShieldCheck,
  RefreshCw,
} from "lucide-react";
import { getActions, type Action } from "@/lib/api";

function getRiskVariant(risk: string): "destructive" | "warning" | "secondary" {
  switch (risk.toLowerCase()) {
    case "high":
      return "destructive";
    case "medium":
      return "warning";
    default:
      return "secondary";
  }
}

function getRiskIcon(risk: string) {
  switch (risk.toLowerCase()) {
    case "high":
      return <AlertTriangle className="h-4 w-4 text-destructive" />;
    case "medium":
      return <ShieldCheck className="h-4 w-4 text-yellow-500" />;
    default:
      return <CheckCircle className="h-4 w-4 text-green-500" />;
  }
}

export default function ActionsPage() {
  const [actions, setActions] = useState<Action[]>([]);
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState<string | null>(null);

  const loadActions = async () => {
    setLoading(true);
    try {
      const data = await getActions();
      setActions(data);
    } catch (error) {
      console.error("Failed to load actions:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadActions();
  }, []);

  const handleDryRun = async (action: Action) => {
    setExecuting(action.id);
    // In a real implementation, this would call the API
    setTimeout(() => {
      setExecuting(null);
      alert(`Dry run completed for: ${action.name}`);
    }, 1500);
  };

  const handleApprove = async (action: Action) => {
    setExecuting(action.id);
    // In a real implementation, this would call the API
    setTimeout(() => {
      setExecuting(null);
      alert(`Action approved: ${action.name}`);
    }, 1000);
  };

  const handleExecute = async (action: Action) => {
    if (!confirm(`Are you sure you want to execute: ${action.name}?`)) {
      return;
    }
    setExecuting(action.id);
    // In a real implementation, this would call the API
    setTimeout(() => {
      setExecuting(null);
      alert(`Action executed: ${action.name}`);
    }, 2000);
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Actions</h1>
          <p className="text-muted-foreground">
            Recommended validation and remediation actions
          </p>
        </div>
        <Button variant="outline" onClick={loadActions} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
          Refresh
        </Button>
      </div>

      {/* Quick Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Total Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{actions.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">
              Requires Approval
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {actions.filter((a) => a.requires_approval).length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">High Risk</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive">
              {
                actions.filter((a) => a.risk.toLowerCase() === "high").length
              }
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Actions List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Play className="h-5 w-5" />
            Pending Actions
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-muted-foreground">
              Loading actions...
            </div>
          ) : actions.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No actions pending. Run an investigation to generate recommended
              actions.
            </div>
          ) : (
            <ScrollArea className="h-[500px]">
              <div className="space-y-4">
                {actions.map((action) => (
                  <div
                    key={action.id}
                    className="border rounded-lg p-4 space-y-3"
                  >
                    <div className="flex items-start justify-between">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          {getRiskIcon(action.risk)}
                          <span className="font-medium">{action.name}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant={getRiskVariant(action.risk)}>
                            {action.risk} Risk
                          </Badge>
                          {action.requires_approval && (
                            <Badge variant="outline">Requires Approval</Badge>
                          )}
                          {action.intent && (
                            <Badge variant="secondary">{action.intent}</Badge>
                          )}
                        </div>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {action.id}
                      </span>
                    </div>

                    <div className="flex items-center gap-2 pt-2 border-t">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleDryRun(action)}
                        disabled={executing === action.id}
                      >
                        {executing === action.id ? (
                          <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
                        ) : (
                          <Play className="h-4 w-4 mr-1" />
                        )}
                        Dry Run
                      </Button>
                      {action.requires_approval ? (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleApprove(action)}
                          disabled={executing === action.id}
                        >
                          <ShieldCheck className="h-4 w-4 mr-1" />
                          Approve
                        </Button>
                      ) : (
                        <Button
                          variant="default"
                          size="sm"
                          onClick={() => handleExecute(action)}
                          disabled={executing === action.id}
                        >
                          <CheckCircle className="h-4 w-4 mr-1" />
                          Execute
                        </Button>
                      )}
                    </div>
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
