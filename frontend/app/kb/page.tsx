"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Search } from "lucide-react";
import { api } from "@/lib/api";
import type { KbEntry } from "@/lib/types";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";

const ease = [0.16, 1, 0.3, 1] as const;

export default function KnowledgeBasePage() {
  const [query, setQuery] = useState("");
  const [entries, setEntries] = useState<KbEntry[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = (q: string) => {
    setLoading(true);
    setError(null);
    api
      .kb(q)
      .then((rows) => {
        setEntries(rows);
        setLoading(false);
      })
      .catch((e) => {
        setError(String(e.message ?? e));
        setLoading(false);
      });
  };

  useEffect(() => {
    load("");
  }, []);

  const onChange = (value: string) => {
    setQuery(value);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => load(value.trim()), 320);
  };

  return (
    <div>
      <div className="mb-7">
        <h1 className="text-[length:var(--text-xl)] font-semibold tracking-[-0.02em]">
          Knowledge base
        </h1>
        <p className="mt-1.5 text-[length:var(--text-sm)] text-muted-foreground">
          Real semantic search over Vectorize — not a client-side filter.
        </p>
      </div>

      <div className="relative mb-7 max-w-md">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={query}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Search the knowledge base…"
          className="pl-8"
        />
      </div>

      {error ? (
        <p className="text-[length:var(--text-xs)] text-muted-foreground">
          Could not reach the knowledge base: {error}
        </p>
      ) : loading ? (
        <div className="space-y-px">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      ) : !entries || entries.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-lg bg-card px-5 py-16 text-center">
          <p className="text-[length:var(--text-xs)] text-muted-foreground">No matching entries.</p>
        </div>
      ) : (
        <div>
          {!query && (
            <p className="mb-3 text-[length:var(--text-2xs)] text-muted-foreground">
              Showing a sample of {entries.length} entries — search to find more.
            </p>
          )}
          <div className="hairline-grid grid-cols-1">
            {entries.map((entry, i) => (
              <motion.div
                key={entry.id}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.25, delay: i * 0.02, ease }}
                className="bg-card px-5 py-4"
              >
                <div className="mb-1.5 flex items-center gap-2 font-mono text-[length:var(--text-2xs)] text-muted-foreground">
                  <span className="truncate">{entry.id}</span>
                  {entry.score !== null && (
                    <span className="shrink-0 text-brand">match {entry.score.toFixed(2)}</span>
                  )}
                </div>
                <p className="text-[length:var(--text-sm)] leading-[1.6] text-foreground">
                  {entry.text.slice(0, 600)}
                  {entry.text.length > 600 ? "…" : ""}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
