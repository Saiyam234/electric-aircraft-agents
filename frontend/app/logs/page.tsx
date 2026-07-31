"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { LogEvent } from "@/lib/types";
import { Skeleton } from "@/components/ui/skeleton";
import { usePageSearch } from "@/lib/search-context";
import { cn } from "@/lib/utils";

const FILTERS: { key: string; label: string }[] = [
  { key: "all", label: "All" },
  { key: "escalation", label: "Escalations" },
  { key: "decision_request", label: "Decisions" },
  { key: "decision_answer", label: "Answers" },
  { key: "agent_start", label: "Agent start" },
  { key: "agent_end", label: "Agent end" },
  { key: "requirement_decision", label: "Requirements" },
];

const dotColor: Record<string, string> = {
  escalation: "bg-destructive",
  decision_request: "bg-brand",
  decision_answer: "bg-brand",
};

export default function LogsPage() {
  const [events, setEvents] = useState<LogEvent[] | null>(null);
  const [filter, setFilter] = useState("all");
  const search = usePageSearch().toLowerCase();

  useEffect(() => {
    api.logs(150).then(setEvents).catch(() => setEvents([]));
  }, []);

  const visible = useMemo(() => {
    if (!events) return [];
    return events.filter((e) => {
      if (filter !== "all" && e.event_type !== filter) return false;
      if (search && !`${e.agent} ${e.description}`.toLowerCase().includes(search)) return false;
      return true;
    });
  }, [events, filter, search]);

  if (!events) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-7 w-40" />
        <Skeleton className="h-4 w-72" />
        <Skeleton className="mt-6 h-96 w-full" />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-7">
        <h1 className="text-[length:var(--text-xl)] font-semibold tracking-[-0.02em]">
          Activity log
        </h1>
        <p className="mt-1.5 text-[length:var(--text-sm)] text-muted-foreground">
          Every real event written to D1, newest first.
        </p>
      </div>

      <div className="mb-7 flex flex-wrap gap-1.5">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={cn(
              "rounded-full border px-3 py-1 text-[length:var(--text-2xs)] font-medium transition-colors",
              filter === f.key
                ? "border-foreground bg-foreground text-background"
                : "border-border text-muted-foreground hover:text-foreground"
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="relative space-y-5 border-l border-border pl-5">
        {visible.map((e, i) => (
          <div key={i} className="relative">
            <span
              className={cn(
                "absolute -left-[23px] top-1.5 h-2 w-2 rounded-full border-2 border-background",
                dotColor[e.event_type] ?? "bg-border"
              )}
            />
            <div className="mb-1 flex flex-wrap items-center gap-2 text-[length:var(--text-2xs)] text-muted-foreground">
              <span className="font-mono">{e.event_type}</span>
              <span>{e.agent}</span>
              <span>{e.timestamp.slice(0, 19)}</span>
            </div>
            <p className="text-[length:var(--text-sm)] leading-[1.55] text-foreground">
              {e.description.slice(0, 280)}
              {e.description.length > 280 ? "…" : ""}
            </p>
          </div>
        ))}
        {visible.length === 0 && (
          <p className="text-[length:var(--text-xs)] text-muted-foreground">No matching events.</p>
        )}
      </div>
    </div>
  );
}
