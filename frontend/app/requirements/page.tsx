"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { api } from "@/lib/api";
import type { RequirementsResponse } from "@/lib/types";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { useCountsRefresh } from "@/lib/counts-context";
import { usePageSearch } from "@/lib/search-context";
import { ClipboardCheck } from "lucide-react";

const ease = [0.16, 1, 0.3, 1] as const;

export default function RequirementsPage() {
  const [data, setData] = useState<RequirementsResponse | null>(null);
  const [pending, setPending] = useState<number | null>(null);
  const refresh = useCountsRefresh();
  const search = usePageSearch().toLowerCase();

  useEffect(() => {
    api.requirements().then(setData).catch(() => setData({ status_counts: {}, proposed: [] }));
  }, []);

  const decide = async (id: number, decision: "approved" | "rejected") => {
    setPending(id);
    try {
      await api.decideRequirement(id, decision);
      setData((prev) =>
        prev
          ? {
              status_counts: {
                ...prev.status_counts,
                proposed: (prev.status_counts.proposed ?? prev.proposed.length) - 1,
                [decision]: (prev.status_counts[decision] ?? 0) + 1,
              },
              proposed: prev.proposed.filter((r) => r.id !== id),
            }
          : prev
      );
      toast.success(`Requirement #${id} ${decision}`);
      refresh();
    } catch (e) {
      toast.error("Could not save that decision", { description: String(e) });
    } finally {
      setPending(null);
    }
  };

  if (!data) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-7 w-52" />
        <Skeleton className="h-4 w-80" />
        <Skeleton className="mt-6 h-32 w-full" />
      </div>
    );
  }

  const visible = data.proposed.filter(
    (r) => !search || r.text.toLowerCase().includes(search)
  );

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-[length:var(--text-xl)] font-semibold tracking-[-0.02em]">
          Requirements
        </h1>
        <p className="mt-1.5 text-[length:var(--text-sm)] text-muted-foreground">
          Agents propose; only you approve. {data.proposed.length} awaiting review.
        </p>
      </div>

      <div className="mb-9 flex flex-wrap gap-10 border-b border-border pb-7">
        {Object.entries(data.status_counts)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([status, n]) => (
            <div key={status}>
              <div className="tabular font-mono text-[length:var(--text-xl)] font-semibold tracking-[-0.02em]">
                {n}
              </div>
              <div className="mt-1 text-[length:var(--text-2xs)] capitalize text-muted-foreground">
                {status}
              </div>
            </div>
          ))}
      </div>

      {visible.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-lg bg-card px-5 py-16 text-center">
          <ClipboardCheck className="h-5 w-5 opacity-50" />
          <p className="text-[length:var(--text-xs)] text-muted-foreground">None pending.</p>
        </div>
      ) : (
        <div className="space-y-2">
          <AnimatePresence initial={false}>
            {visible.map((r, i) => (
              <motion.div
                key={r.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, height: 0, marginBottom: 0 }}
                transition={{ duration: 0.3, delay: i * 0.03, ease }}
                className="rounded-lg border border-border bg-card p-4 shadow-sm transition-colors"
              >
                <div className="mb-1.5 flex items-center gap-2 text-[length:var(--text-2xs)] text-muted-foreground">
                  <span className="font-mono">#{r.id}</span>
                  <span>{r.created_at.slice(0, 19)}</span>
                </div>
                <p className="text-[length:var(--text-base)] leading-[1.55]">{r.text}</p>
                {r.impact_assessment && (
                  <p className="mt-2 text-[length:var(--text-xs)] leading-[1.6] text-muted-foreground">
                    <span className="font-medium text-foreground">Impact — </span>
                    {r.impact_assessment}
                  </p>
                )}
                <div className="mt-3.5 flex gap-2">
                  <Button
                    variant="success"
                    size="sm"
                    onClick={() => decide(r.id, "approved")}
                    disabled={pending === r.id}
                  >
                    Approve
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => decide(r.id, "rejected")}
                    disabled={pending === r.id}
                  >
                    Reject
                  </Button>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
