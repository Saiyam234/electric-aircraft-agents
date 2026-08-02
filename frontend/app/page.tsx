"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Overview as OverviewData } from "@/lib/types";
import { Sparkline } from "@/components/sparkline";
import { Ring } from "@/components/ring";
import { AnimatedNumber } from "@/components/animated-number";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertTriangle, CircleHelp } from "lucide-react";

const ease = [0.16, 1, 0.3, 1] as const;

function fmtDuration(seconds: number | null): string {
  if (seconds === null) return "—";
  const s = Math.max(0, Math.round(seconds));
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return rem ? `${m}m ${rem}s` : `${m}m`;
}

const statusDotClass: Record<string, string> = {
  ok: "bg-success",
  warn: "bg-warning",
  bad: "bg-destructive",
};

export default function OverviewPage() {
  const [data, setData] = useState<OverviewData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .overview()
      .then(setData)
      .catch((e) => setError(String(e.message ?? e)));
  }, []);

  if (error) {
    return (
      <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border py-20 text-center">
        <AlertTriangle className="h-5 w-5 text-muted-foreground" />
        <p className="text-[length:var(--text-sm)] text-muted-foreground">
          Could not reach the backend API. Is <code className="font-mono">backend/api.py</code>{" "}
          running on port 5001?
        </p>
        <p className="text-[length:var(--text-2xs)] text-muted-foreground/70">{error}</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="space-y-8">
        <div className="space-y-2">
          <Skeleton className="h-7 w-56" />
          <Skeleton className="h-4 w-80" />
        </div>
        <Skeleton className="h-[260px] w-full" />
      </div>
    );
  }

  const builtPct = (100 * data.agents_built) / data.roster_total;

  return (
    <div>
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease }}
        className="mb-2"
      >
        <h1 className="text-[length:var(--text-xl)] font-semibold tracking-[-0.02em]">
          {data.greeting}, Saiyam
        </h1>
        <div className="mt-2 flex items-center gap-2 text-[length:var(--text-sm)] text-muted-foreground">
          <span className={`h-1.5 w-1.5 rounded-full ${statusDotClass[data.status.level]}`} />
          {data.status.text}
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.08, ease }}
        className="hairline-grid my-6 grid-cols-1 md:grid-cols-[1.7fr_1fr]"
      >
        <div className="flex flex-col bg-card px-5 pb-4 pt-5">
          <span className="text-[length:var(--text-2xs)] font-semibold uppercase tracking-[0.06em] text-muted-foreground">
            Total spend
          </span>
          <AnimatedNumber
            value={data.total_cost}
            prefix="$"
            decimals={2}
            className="tabular mt-1.5 font-mono text-[length:var(--text-display)] font-semibold leading-none tracking-[-0.02em]"
          />
          <div className="mb-1 mt-4">
            <Sparkline values={data.spend_series} />
          </div>
          <p className="mt-auto pt-3 text-[length:var(--text-xs)] text-muted-foreground">
            ${data.recent_cost_7d.toFixed(2)} in the last 7 days · {data.recent_runs_7d} of{" "}
            {data.total_runs} runs
          </p>
        </div>
        <div className="flex flex-col bg-card">
          <StatRow label="Run success">
            {data.success_rate !== null ? `${data.success_rate.toFixed(0)}%` : "—"}
          </StatRow>
          <StatRow label="Avg. run time">{fmtDuration(data.avg_runtime_seconds)}</StatRow>
          <StatRow label="Agents built" sub={`${data.agents_built} of ${data.roster_total}`}>
            <Ring pct={builtPct} />
          </StatRow>
          <StatRow label="Knowledge base">
            {data.kb_count !== null ? data.kb_count : "—"}
          </StatRow>
          <StatRow label="Awaiting you" accent={data.open_decisions_count > 0}>
            {data.open_decisions_count}
          </StatRow>
        </div>
      </motion.div>

      <Section title="Escalations">
        {data.escalations.length === 0 ? (
          <EmptyState text="None. Safety, regulatory and irreversible-cost issues appear here the moment they are raised." />
        ) : (
          <div className="space-y-2">
            {data.escalations.map((e, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: i * 0.04, ease }}
                className="rounded-lg border border-l-[3px] border-border border-l-destructive bg-card p-4 shadow-sm"
              >
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <span className="rounded-full bg-destructive-soft px-2 py-0.5 text-[length:var(--text-2xs)] font-semibold uppercase tracking-[0.04em] text-destructive">
                    Escalation
                  </span>
                  <span className="text-[length:var(--text-2xs)] text-muted-foreground">{e.agent}</span>
                  <span className="font-mono text-[length:var(--text-2xs)] text-muted-foreground/80">
                    {e.timestamp.slice(0, 19).replace("T", " ")}
                  </span>
                </div>
                <p className="text-[length:var(--text-base)] leading-[1.6]">{e.description}</p>
              </motion.div>
            ))}
          </div>
        )}
      </Section>

      <Section title="Decisions waiting on you" className="mt-9">
        {data.open_decisions_count === 0 ? (
          <EmptyState text="Nothing queued." icon={<CircleHelp className="h-5 w-5 opacity-50" />} />
        ) : (
          <Link
            href="/decisions"
            className="flex items-center justify-between rounded-lg border border-l-[3px] border-border border-l-brand bg-card p-4 shadow-sm transition-colors hover:bg-accent/30"
          >
            <span className="flex items-center gap-2">
              <span className="rounded-full bg-brand-soft px-2 py-0.5 text-[length:var(--text-2xs)] font-semibold uppercase tracking-[0.04em] text-brand">
                Decision
              </span>
              <span className="text-[length:var(--text-base)] font-medium">
                {data.open_decisions_count} decision{data.open_decisions_count === 1 ? "" : "s"} queued
              </span>
            </span>
            <span className="text-[length:var(--text-xs)] text-muted-foreground">View →</span>
          </Link>
        )}
      </Section>
    </div>
  );
}

function StatRow({
  label,
  sub,
  accent,
  children,
}: {
  label: string;
  sub?: string;
  accent?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-border px-5 py-3.5 transition-colors last:border-b-0 hover:bg-accent/30">
      <div className="flex flex-col gap-1">
        <span className="text-[length:var(--text-xs)] text-muted-foreground">{label}</span>
        {sub && <span className="tabular font-mono text-[length:var(--text-2xs)] text-muted-foreground">{sub}</span>}
      </div>
      <span
        className={`tabular font-mono text-[length:var(--text-lg)] font-semibold tracking-[-0.01em] ${accent ? "text-brand" : ""}`}
      >
        {children}
      </span>
    </div>
  );
}

function Section({
  title,
  className,
  children,
}: {
  title: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={className}>
      <h2 className="mb-3 text-[length:var(--text-2xs)] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
        {title}
      </h2>
      {children}
    </div>
  );
}

function EmptyState({ text, icon }: { text: string; icon?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-lg bg-card px-5 py-10 text-center">
      {icon}
      <p className="max-w-[360px] text-[length:var(--text-xs)] text-muted-foreground">{text}</p>
    </div>
  );
}
