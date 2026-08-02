"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { RosterAgent } from "@/lib/types";
import { Skeleton } from "@/components/ui/skeleton";
import { AgentGraph } from "@/components/agent-graph";

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
      <div className="mb-6">
        <h1 className="text-[length:var(--text-xl)] font-semibold tracking-[-0.02em]">
          Agent roster
        </h1>
        <p className="mt-1.5 text-[length:var(--text-sm)] text-muted-foreground">
          {builtCount} of 19 built
          {errorAgents.length > 0
            ? ` · ${errorAgents.length} with a real error`
            : " · no real errors on record"}
          . Drag the canvas to pan, scroll to zoom, hover to trace a path, click a node or edge for details.
        </p>
      </div>

      <AgentGraph roster={roster} />
    </div>
  );
}
