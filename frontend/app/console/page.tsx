"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { api } from "@/lib/api";
import type { RunJob, RunnableAgent } from "@/lib/types";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { AlertTriangle, Loader2, CheckCircle2, XCircle, TerminalSquare } from "lucide-react";

const ease = [0.16, 1, 0.3, 1] as const;

const MODE_LABEL: Record<string, string> = {
  directive: "Takes a directive",
  topic: "Takes a research topic",
  innovation: "Takes a candidate innovation",
  none: "Runs its fixed pass against current state",
};

const MODE_PLACEHOLDER: Record<string, string> = {
  directive: 'e.g. "Assess whether Wave 4 can be sequenced given the open blockers"',
  topic: 'e.g. "battery thermal runaway propagation in small packs"',
  innovation: 'e.g. "Switch to a lighter spar layup to reduce structural mass"',
  none: "",
};

export default function ConsolePage() {
  const [agents, setAgents] = useState<RunnableAgent[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [job, setJob] = useState<RunJob | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const outputRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.runnableAgents().then(setAgents).catch(() => setAgents([]));
  }, []);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  useEffect(() => {
    outputRef.current?.scrollTo({ top: outputRef.current.scrollHeight });
  }, [job?.output.length]);

  const current = agents?.find((a) => a.agent === selected) ?? null;
  const needsInput = current && current.mode !== "none";
  const isRunning = job?.status === "running";

  const startPolling = (jobId: string) => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const j = await api.getRun(jobId);
        setJob(j);
        if (j.status !== "running" && pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
          if (j.status === "done") toast.success(`${j.agent} finished`);
          else toast.error(`${j.agent} exited with an error`);
        }
      } catch {
        // transient network hiccup — keep polling, don't kill the UI over one miss
      }
    }, 1400);
  };

  const launch = async () => {
    if (!current) return;
    setConfirming(false);
    try {
      const { job_id } = await api.startRun(current.agent, needsInput ? input : null);
      setJob({
        id: job_id,
        agent: current.agent,
        module: "",
        mode: current.mode,
        input: needsInput ? input : null,
        status: "running",
        output: [],
        started_at: Date.now() / 1000,
        finished_at: null,
        exit_code: null,
        pid: null,
      });
      startPolling(job_id);
    } catch (e) {
      toast.error("Could not start the run", { description: String(e) });
    }
  };

  const selectAgent = (agent: string) => {
    setSelected(agent);
    setInput("");
    setJob(null);
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  if (!agents) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-7 w-40" />
        <Skeleton className="h-4 w-96" />
        <Skeleton className="mt-6 h-64 w-full" />
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8 max-w-2xl">
        <h1 className="text-[length:var(--text-xl)] font-semibold tracking-[-0.02em]">Console</h1>
        <p className="mt-1.5 text-[length:var(--text-sm)] leading-[1.6] text-muted-foreground">
          Dispatch a real agent run and watch its output stream in. This isn&apos;t a chat — every
          agent here is a one-shot batch process against live Cloudflare data, and every run costs
          real money.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-px lg:grid-cols-[260px_1fr]">
        <nav className="hairline-grid grid-cols-1 self-start lg:sticky lg:top-[76px]" aria-label="Runnable agents">
          {agents.map((a) => (
            <button
              key={a.agent}
              onClick={() => selectAgent(a.agent)}
              aria-current={selected === a.agent ? "true" : undefined}
              className={cn(
                "flex flex-col gap-0.5 bg-card px-4 py-3 text-left transition-colors hover:bg-accent/30",
                selected === a.agent && "bg-accent/50"
              )}
            >
              <span className="text-[length:var(--text-sm)] font-medium">{a.agent}</span>
              <span className="text-[length:var(--text-2xs)] text-muted-foreground">
                {a.run_count > 0 ? `avg $${a.avg_cost?.toFixed(2)} · ${a.run_count} run${a.run_count === 1 ? "" : "s"}` : "not yet run"}
              </span>
            </button>
          ))}
        </nav>

        <div className="lg:pl-6">
          {!current ? (
            <div className="flex h-72 flex-col items-center justify-center gap-2 text-center">
              <TerminalSquare className="h-5 w-5 text-muted-foreground/50" />
              <p className="text-[length:var(--text-xs)] text-muted-foreground">
                Pick an agent to dispatch a real run.
              </p>
            </div>
          ) : (
            <motion.div
              key={current.agent}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, ease }}
            >
              <div className="mb-1 flex items-baseline justify-between">
                <h2 className="text-[length:var(--text-lg)] font-semibold tracking-[-0.01em]">
                  {current.agent}
                </h2>
                {current.run_count > 0 && (
                  <span className="text-[length:var(--text-2xs)] text-muted-foreground">
                    typical ${current.min_cost?.toFixed(2)}–${current.max_cost?.toFixed(2)}
                  </span>
                )}
              </div>
              <p className="mb-4 text-[length:var(--text-xs)] text-muted-foreground">
                {MODE_LABEL[current.mode]}
              </p>

              {needsInput && (
                <Textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={MODE_PLACEHOLDER[current.mode]}
                  rows={3}
                  disabled={isRunning}
                  className="mb-4"
                />
              )}

              <Button
                onClick={() => setConfirming(true)}
                disabled={(needsInput && !input.trim()) || isRunning}
              >
                {isRunning ? "Running…" : "Run"}
              </Button>

              {job && (
                <div className="mt-6 border-t border-border pt-4">
                  <div className="mb-2.5 flex items-center gap-2">
                    {job.status === "running" && (
                      <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
                    )}
                    {job.status === "done" && <CheckCircle2 className="h-3.5 w-3.5 text-success" />}
                    {job.status === "error" && <XCircle className="h-3.5 w-3.5 text-destructive" />}
                    <span className="text-[length:var(--text-2xs)] text-muted-foreground">
                      {job.status === "running"
                        ? "Real Claude Agent SDK call in progress"
                        : job.status === "done"
                          ? "Finished"
                          : "Exited with an error"}
                    </span>
                  </div>
                  <div
                    ref={outputRef}
                    className="max-h-[440px] overflow-y-auto rounded-lg bg-accent/30 px-4 py-3 font-mono text-[12px] leading-[1.65]"
                  >
                    {job.output.length === 0 ? (
                      <span className="text-muted-foreground">waiting for output…</span>
                    ) : (
                      job.output.map((line, i) => (
                        <div key={i} className="whitespace-pre-wrap break-words text-foreground/85">
                          {line}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </motion.div>
          )}
        </div>
      </div>

      <Dialog open={confirming} onOpenChange={setConfirming}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <div className="flex items-center gap-2 text-warning">
              <AlertTriangle className="h-4 w-4" />
              <DialogTitle>Real spend, real run</DialogTitle>
            </div>
            <DialogDescription className="pt-1 leading-[1.6]">
              This dispatches a real Claude Agent SDK call for <strong className="text-foreground">{current?.agent}</strong> against
              live Cloudflare data.{" "}
              {current && current.run_count > 0
                ? `Past runs cost $${current.min_cost?.toFixed(2)}–$${current.max_cost?.toFixed(2)}.`
                : "No prior runs — cost is unknown."}{" "}
              Not reversible once started.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="bg-transparent border-none mx-0 mb-0 p-0 pt-2">
            <Button variant="outline" onClick={() => setConfirming(false)}>
              Cancel
            </Button>
            <Button onClick={launch}>Confirm &amp; run</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
