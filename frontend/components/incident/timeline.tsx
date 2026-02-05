"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { TimelineItem } from "@/lib/api";

interface TimelineProps {
  items: TimelineItem[];
}

function getKindColor(kind?: string): string {
  switch (kind) {
    case "alert":
      return "bg-red-500";
    case "log":
      return "bg-blue-500";
    case "metric":
      return "bg-green-500";
    case "deployment":
      return "bg-purple-500";
    case "change":
      return "bg-orange-500";
    case "build":
      return "bg-yellow-500";
    case "event":
      return "bg-cyan-500";
    case "trace":
      return "bg-pink-500";
    default:
      return "bg-gray-500";
  }
}

export function Timeline({ items }: TimelineProps) {
  if (items.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No timeline events.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Timeline
          <Badge variant="secondary">{items.length} events</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[400px]">
          <div className="relative ml-3">
            {/* Vertical line */}
            <div className="absolute left-0 top-0 h-full w-0.5 bg-border" />

            <div className="space-y-4">
              {items.map((item, index) => (
                <div key={index} className="relative pl-6">
                  {/* Dot */}
                  <div
                    className={`absolute left-[-4px] top-1.5 h-3 w-3 rounded-full ${getKindColor(
                      item.kind
                    )}`}
                  />

                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-muted-foreground">
                        {item.time}
                      </span>
                      <Badge variant="outline" className="text-xs">
                        {item.source}
                      </Badge>
                      {item.kind && (
                        <Badge variant="secondary" className="text-xs">
                          {item.kind}
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm">{item.label}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
