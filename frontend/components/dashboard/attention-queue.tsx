"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { AlertTriangle, ArrowRight } from "lucide-react";

interface AttentionItem {
  id: string;
  title: string;
  severity: string;
  environment: string;
  updated_at: string;
}

interface AttentionQueueProps {
  items: AttentionItem[];
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

export function AttentionQueue({ items }: AttentionQueueProps) {
  if (items.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            Attention Queue
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No incidents requiring attention.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <AlertTriangle className="h-5 w-5" />
          Attention Queue
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[300px]">
          <div className="space-y-3">
            {items.map((item) => (
              <div
                key={item.id}
                className="flex items-center justify-between rounded-lg border p-3"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Badge variant={getSeverityVariant(item.severity)}>
                      {item.severity}
                    </Badge>
                    <Badge variant="outline">{item.environment}</Badge>
                  </div>
                  <p className="text-sm font-medium">{item.title}</p>
                  <p className="text-xs text-muted-foreground">
                    Updated {item.updated_at}
                  </p>
                </div>
                <Button variant="ghost" size="sm" asChild>
                  <Link href={`/incident/${item.id}`}>
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
