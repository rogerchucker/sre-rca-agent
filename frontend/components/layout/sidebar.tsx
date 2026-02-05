"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  AlertTriangle,
  BookOpen,
  Activity,
  Play,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
  TooltipProvider,
} from "@/components/ui/tooltip";

const navigation = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Incidents", href: "/incident", icon: AlertTriangle },
  { name: "Knowledge", href: "/knowledge", icon: BookOpen },
  { name: "Signals", href: "/signals", icon: Activity },
  { name: "Actions", href: "/action", icon: Play },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <TooltipProvider>
      <aside className="fixed left-0 top-0 z-40 flex h-screen w-16 flex-col border-r bg-background">
        <div className="flex h-16 items-center justify-center border-b">
          <Link href="/" className="flex items-center justify-center">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <AlertTriangle className="h-5 w-5" />
            </div>
          </Link>
        </div>
        <nav className="flex flex-1 flex-col items-center gap-2 p-2">
          {navigation.map((item) => {
            const isActive =
              pathname === item.href ||
              (item.href !== "/" && pathname.startsWith(item.href));
            return (
              <Tooltip key={item.name}>
                <TooltipTrigger asChild>
                  <Link
                    href={item.href}
                    className={cn(
                      "flex h-10 w-10 items-center justify-center rounded-lg transition-colors",
                      isActive
                        ? "bg-accent text-accent-foreground"
                        : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                    )}
                  >
                    <item.icon className="h-5 w-5" />
                    <span className="sr-only">{item.name}</span>
                  </Link>
                </TooltipTrigger>
                <TooltipContent side="right">{item.name}</TooltipContent>
              </Tooltip>
            );
          })}
        </nav>
        <div className="flex flex-col items-center gap-2 p-2 border-t">
          <Tooltip>
            <TooltipTrigger asChild>
              <Link
                href="/settings"
                className="flex h-10 w-10 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
              >
                <Settings className="h-5 w-5" />
                <span className="sr-only">Settings</span>
              </Link>
            </TooltipTrigger>
            <TooltipContent side="right">Settings</TooltipContent>
          </Tooltip>
        </div>
      </aside>
    </TooltipProvider>
  );
}
