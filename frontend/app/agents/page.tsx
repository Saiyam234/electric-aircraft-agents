"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { RosterAgent } from "@/lib/types";
import { Skeleton } from "@/components/ui/skeleton";
import { AgentGraph } from "@/components/agent-graph";
import { DIVISION_COLOR } from "@/lib/graph-data";

export default function AgentsPage() {
  const [roster, setRoster] = useState<RosterAgent[] | null>(null);

  useEffect(() => {
    api.roster().then(setRoster).catch(() => setRoster([]));
  }, []);

  const builtCount = roster?.filter((a) => a.built).length ?? 0;
  const errorAgents = roster?.filter((a) => a.error_count > 0) ?? [];

  if (!roster) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-7 w-52" />
        <Skeleton className="h-4 w-96" />
        <Skeleton className="mt-6 h-[520px] w-full" />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[length:var(--text-xl)] font-semibold tracking-[-0.02em]">
            Agent roster
          </h1>
          <p className="mt-1.5 text-[length:var(--text-sm)] text-muted-foreground">
            {builtCount} of 19 built
            {errorAgents.length > 0
              ? ` · ${errorAgents.length} with a real error`
              : " · no real errors on record"}
            . Drag nodes, scroll to zoom, hover to trace a path, click for details.
          </p>
        </div>
        <div className="flex flex-wrap gap-x-4 gap-y-1.5">
          {Object.entries(DIVISION_COLOR).map(([division, color]) => (
            <div key={division} className="flex items-center gap-1.5 text-[length:var(--text-2xs)] text-muted-foreground">
              <span
                className="h-1.5 w-1.5 rounded-full"
                style={{ background: color }}
              />
              {division}
            </div>
          ))}
        </div>
      </div>

      <AgentGraph roster={roster} />
    </div>
  );
}
