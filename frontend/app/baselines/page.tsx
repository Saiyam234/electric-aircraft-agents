"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Baseline } from "@/lib/types";
import { Skeleton } from "@/components/ui/skeleton";
import { usePageSearch } from "@/lib/search-context";

export default function BaselinesPage() {
  const [baselines, setBaselines] = useState<Baseline[] | null>(null);
  const search = usePageSearch().toLowerCase();

  useEffect(() => {
    api.baselines().then(setBaselines).catch(() => setBaselines([]));
  }, []);

  if (!baselines) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-7 w-40" />
        <Skeleton className="h-4 w-96" />
        <Skeleton className="mt-6 h-64 w-full" />
      </div>
    );
  }

  const visible = baselines.filter(
    (b) => !search || b.version.toLowerCase().includes(search) || String(b.id).includes(search)
  );

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-[length:var(--text-xl)] font-semibold tracking-[-0.02em]">Baselines</h1>
        <p className="mt-1.5 text-[length:var(--text-sm)] text-muted-foreground">
          All three Assurance Gate offices exist now, but none has signed off on a baseline yet —
          the current one is still pending re-derivation to the decided 1.40 m span.
        </p>
      </div>

      <div className="overflow-x-auto rounded-lg border border-border bg-card shadow-sm">
        <table className="w-full text-[length:var(--text-sm)]">
          <thead>
            <tr className="border-b border-border text-left text-[length:var(--text-2xs)] uppercase tracking-[0.06em] text-muted-foreground">
              <th className="py-3 pr-4 pl-5 font-medium">ID</th>
              <th className="py-3 pr-4 font-medium">Version</th>
              <th className="py-3 pr-4 font-medium">Status</th>
              <th className="py-3 pr-4 font-medium">Assurance</th>
              <th className="py-3 pr-5 font-medium">Created</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((b) => (
              <tr key={b.id} className="border-b border-border transition-colors last:border-b-0 hover:bg-accent/30">
                <td className="py-3 pr-4 pl-5 font-mono text-muted-foreground">{b.id}</td>
                <td className="py-3 pr-4 font-mono">{b.version}</td>
                <td className="py-3 pr-4 capitalize">{b.status}</td>
                <td className="py-3 pr-4">
                  {b.stamped ? (
                    <span className="text-success">Stamped</span>
                  ) : (
                    <span className="text-muted-foreground">0 of 3 offices</span>
                  )}
                </td>
                <td className="py-3 pr-5 text-muted-foreground">{b.created_at.slice(0, 19)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
