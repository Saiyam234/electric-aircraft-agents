"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";
import { toast } from "sonner";
import { api } from "@/lib/api";
import type {
  AgentGraphEdge,
  PipelineInfo,
  PipelineJob,
  PipelineStep,
  RunJob,
  RunnableAgent,
} from "@/lib/types";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import {
  AlertTriangle,
  CheckCircle2,
  Circle,
  Loader2,
  RotateCcw,
  Send,
  TerminalSquare,
  XCircle,
} from "lucide-react";

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

// storage._now() stores Python's datetime.now(timezone.utc).isoformat(), which
// ends "+00:00", not "Z". Matching that suffix keeps the ?since= string
// lexicographically comparable to real stored timestamps at the SQL layer —
// a plain toISOString() would end "Z" and could misorder events that land in
// the same second as the pipeline's own start.
function toBackendIso(unixSeconds: number): string {
  return new Date(unixSeconds * 1000).toISOString().replace("Z", "+00:00");
}

function StatusIcon({ status }: { status: "running" | "done" | "error" }) {
  if (status === "running") return <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />;
  if (status === "done") return <CheckCircle2 className="h-3.5 w-3.5 text-success" />;
  return <XCircle className="h-3.5 w-3.5 text-destructive" />;
}

function OutputPane({ lines, maxHeight = 260 }: { lines: string[]; maxHeight?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight });
  }, [lines.length]);
  return (
    <div
      ref={ref}
      style={{ maxHeight }}
      className="overflow-y-auto rounded-lg bg-accent/30 px-4 py-3 font-mono text-[12px] leading-[1.65]"
    >
      {lines.length === 0 ? (
        <span className="text-muted-foreground">waiting for output…</span>
      ) : (
        lines.map((line, i) => (
          <div key={i} className="whitespace-pre-wrap break-words text-foreground/85">
            {line}
          </div>
        ))
      )}
    </div>
  );
}

// Real communication a step actually received from an earlier step in THIS
// run — an edge only exists if two agents' real D1 events both named the
// same real artifact (see backend/api.py's agents_graph). Restricted to
// agents that already ran earlier in this specific pipeline job, so a stale
// edge from a past unrelated run can't be shown as if it just happened.
function incomingEdgesFor(
  stepIndex: number,
  steps: PipelineStep[],
  edges: AgentGraphEdge[]
): AgentGraphEdge[] {
  const preceding = new Set(steps.slice(0, stepIndex).map((s) => s.agent));
  const target = steps[stepIndex].agent;
  return edges.filter((e) => e.target === target && preceding.has(e.source));
}

function CommBadges({ edges }: { edges: AgentGraphEdge[] }) {
  if (edges.length === 0) return null;
  return (
    <div className="mb-3 flex flex-wrap gap-1.5">
      {edges.map((e) => (
        <motion.div
          key={`${e.source}->${e.target}:${e.artifacts.join(",")}`}
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease }}
        >
          <Badge variant="outline" className="gap-1.5 border-brand/30 text-brand">
            <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-brand" />
            {e.source} sent {e.artifacts.join(", ")}
          </Badge>
        </motion.div>
      ))}
    </div>
  );
}

function CostBadge({ cost, turns }: { cost: number | null; turns: number | null }) {
  if (cost === null) return null;
  return (
    <span className="text-[length:var(--text-2xs)] text-muted-foreground">
      ${cost.toFixed(4)}
      {turns !== null ? ` · ${turns} turn${turns === 1 ? "" : "s"}` : ""}
    </span>
  );
}

export default function ConsolePage() {
  // ---- runnable-agent list (shared by both modes for cost lookups) ----
  const [agents, setAgents] = useState<RunnableAgent[] | null>(null);

  // ---- pipeline mode ----
  const [pipelineInfo, setPipelineInfo] = useState<PipelineInfo | null>(null);
  const [selectedSteps, setSelectedSteps] = useState<string[]>([]);
  const [pipelineMessage, setPipelineMessage] = useState("");
  const [pipelineConfirming, setPipelineConfirming] = useState(false);
  const [pipelineJob, setPipelineJob] = useState<PipelineJob | null>(null);
  const [liveMessage, setLiveMessage] = useState("");
  const [graphEdges, setGraphEdges] = useState<AgentGraphEdge[]>([]);
  const pipelinePollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pipelineSinceRef = useRef<string | null>(null);

  // ---- single-agent mode ----
  const [selected, setSelected] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [singleMessage, setSingleMessage] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [job, setJob] = useState<RunJob | null>(null);
  const singlePollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    api.runnableAgents().then(setAgents).catch(() => setAgents([]));
    api
      .pipelineInfo()
      .then((info) => {
        setPipelineInfo(info);
        setSelectedSteps(info.order);
      })
      .catch(() => setPipelineInfo(null));
  }, []);

  useEffect(() => {
    return () => {
      if (pipelinePollRef.current) clearInterval(pipelinePollRef.current);
      if (singlePollRef.current) clearInterval(singlePollRef.current);
    };
  }, []);

  // ---------------- pipeline mode logic ----------------

  const toggleStep = (agent: string) => {
    if (pipelineJob) return; // locked once a run is in flight
    setSelectedSteps((prev) => {
      const order = pipelineInfo?.order ?? [];
      if (prev.includes(agent)) return prev.filter((a) => a !== agent);
      return order.filter((a) => prev.includes(a) || a === agent);
    });
  };

  const selectedStepInfos = useMemo(
    () => (pipelineInfo?.steps ?? []).filter((s) => selectedSteps.includes(s.agent)),
    [pipelineInfo, selectedSteps]
  );
  const estimatedCost = useMemo(() => {
    const known = selectedStepInfos.map((s) => s.avg_cost).filter((c): c is number => c !== null);
    return known.length > 0 ? known.reduce((a, b) => a + b, 0) : null;
  }, [selectedStepInfos]);
  const unknownStepCount = selectedStepInfos.filter((s) => s.avg_cost === null).length;

  const startPipelinePolling = (jobId: string, sinceIso: string) => {
    if (pipelinePollRef.current) clearInterval(pipelinePollRef.current);
    pipelinePollRef.current = setInterval(async () => {
      try {
        const j = await api.getRun(jobId);
        if (j.kind !== "pipeline") return;
        setPipelineJob(j);
        try {
          const g = await api.agentsGraphSince(sinceIso);
          setGraphEdges(g.edges);
        } catch {
          // graph poll is best-effort — never let it kill the job poll
        }
        if (j.status !== "running" && pipelinePollRef.current) {
          clearInterval(pipelinePollRef.current);
          pipelinePollRef.current = null;
          if (j.status === "done") toast.success("Pipeline finished");
          else toast.error("Pipeline exited with an error");
        }
      } catch {
        // transient network hiccup — keep polling
      }
    }, 1400);
  };

  const launchPipeline = async () => {
    setPipelineConfirming(false);
    const startedAt = Date.now() / 1000;
    const sinceIso = toBackendIso(startedAt);
    try {
      const message = pipelineMessage.trim() || null;
      const { job_id } = await api.startPipeline(selectedSteps, message);
      setPipelineJob({
        id: job_id,
        kind: "pipeline",
        agent: "Pipeline",
        agents: selectedSteps,
        status: "running",
        steps: [],
        current_step: -1,
        pending_message: message,
        started_at: startedAt,
        finished_at: null,
      });
      setGraphEdges([]);
      setPipelineMessage("");
      setLiveMessage("");
      pipelineSinceRef.current = sinceIso;
      startPipelinePolling(job_id, sinceIso);
    } catch (e) {
      toast.error("Could not start the pipeline", { description: String(e) });
    }
  };

  const sendLiveMessage = async () => {
    if (!pipelineJob || !liveMessage.trim()) return;
    const text = liveMessage.trim();
    try {
      await api.sendPipelineMessage(pipelineJob.id, text);
      setLiveMessage("");
      toast.success("Queued for the next step", { description: text });
    } catch (e) {
      toast.error("Could not send the message", { description: String(e) });
    }
  };

  const resetPipeline = () => {
    if (pipelinePollRef.current) {
      clearInterval(pipelinePollRef.current);
      pipelinePollRef.current = null;
    }
    setPipelineJob(null);
    setGraphEdges([]);
    setLiveMessage("");
  };

  const pipelineRunning = pipelineJob?.status === "running";
  const queuedAgents = pipelineJob
    ? pipelineJob.agents.filter((a) => !pipelineJob.steps.some((s) => s.agent === a))
    : [];
  const pipelineTotalCost = pipelineJob
    ? pipelineJob.steps.reduce((sum, s) => sum + (s.cost ?? 0), 0)
    : 0;

  // ---------------- single-agent mode logic ----------------

  const current = agents?.find((a) => a.agent === selected) ?? null;
  const needsInput = current && current.mode !== "none";
  const isRunning = job?.status === "running";

  const startSinglePolling = (jobId: string) => {
    if (singlePollRef.current) clearInterval(singlePollRef.current);
    singlePollRef.current = setInterval(async () => {
      try {
        const j = await api.getRun(jobId);
        if (j.kind !== "single") return;
        setJob(j);
        if (j.status !== "running" && singlePollRef.current) {
          clearInterval(singlePollRef.current);
          singlePollRef.current = null;
          if (j.status === "done") toast.success(`${j.agent} finished`);
          else toast.error(`${j.agent} exited with an error`);
        }
      } catch {
        // transient network hiccup — keep polling
      }
    }, 1400);
  };

  const launch = async () => {
    if (!current) return;
    setConfirming(false);
    const message = singleMessage.trim() || null;
    try {
      const { job_id } = await api.startRun(current.agent, needsInput ? input : null, message);
      setJob({
        id: job_id,
        kind: "single",
        agent: current.agent,
        module: "",
        mode: current.mode,
        input: needsInput ? input : null,
        message,
        status: "running",
        output: [],
        started_at: Date.now() / 1000,
        finished_at: null,
        exit_code: null,
        pid: null,
        cost: null,
        turns: null,
      });
      setSingleMessage("");
      startSinglePolling(job_id);
    } catch (e) {
      toast.error("Could not start the run", { description: String(e) });
    }
  };

  const selectAgent = (agent: string) => {
    setSelected(agent);
    setInput("");
    setSingleMessage("");
    setJob(null);
    if (singlePollRef.current) {
      clearInterval(singlePollRef.current);
      singlePollRef.current = null;
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
          Dispatch real agent runs and watch their real output stream in — one agent at a time, or
          the whole pipeline top to bottom. This isn&apos;t a chat: every agent is a one-shot batch
          process against live Cloudflare data. You can attach a real message before a run starts,
          or send one while a pipeline is in flight for the next step to pick up.
        </p>
      </div>

      <Tabs
        defaultValue="pipeline"
        onValueChange={() => {
          /* mode switch keeps both jobs' state — nothing to reset */
        }}
      >
        <TabsList className="mb-6">
          <TabsTrigger value="pipeline">Full pipeline</TabsTrigger>
          <TabsTrigger value="single">Single agent</TabsTrigger>
        </TabsList>

        {/* ================= PIPELINE MODE ================= */}
        <TabsContent value="pipeline">
          {!pipelineJob ? (
            <div className="max-w-2xl">
              <p className="mb-3 text-[length:var(--text-xs)] font-medium text-foreground">
                Steps ({selectedSteps.length}/{pipelineInfo?.order.length ?? 0}) — click to include or skip
              </p>
              <div className="hairline-grid grid-cols-1 mb-4">
                {(pipelineInfo?.steps ?? []).map((s, i) => {
                  const on = selectedSteps.includes(s.agent);
                  return (
                    <button
                      key={s.agent}
                      onClick={() => toggleStep(s.agent)}
                      className={cn(
                        "flex items-center justify-between gap-3 bg-card px-4 py-2.5 text-left transition-colors hover:bg-accent/30",
                        !on && "opacity-40"
                      )}
                    >
                      <span className="flex items-center gap-2.5">
                        <span className="w-4 text-[length:var(--text-2xs)] text-muted-foreground">
                          {i + 1}
                        </span>
                        <span className="text-[length:var(--text-sm)]">{s.agent}</span>
                      </span>
                      <span className="text-[length:var(--text-2xs)] text-muted-foreground">
                        {s.run_count > 0 ? `avg $${s.avg_cost?.toFixed(2)}` : "not yet run"}
                      </span>
                    </button>
                  );
                })}
              </div>

              <Textarea
                value={pipelineMessage}
                onChange={(e) => setPipelineMessage(e.target.value)}
                placeholder="Optional — a real message for the first step (e.g. a steer for how to approach this run)"
                rows={2}
                className="mb-4"
              />

              <Button
                onClick={() => setPipelineConfirming(true)}
                disabled={selectedSteps.length === 0}
              >
                Run pipeline ({selectedSteps.length} step{selectedSteps.length === 1 ? "" : "s"})
              </Button>
            </div>
          ) : (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.25, ease }}
              className="max-w-2xl"
            >
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {pipelineRunning ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
                  ) : pipelineJob.status === "done" ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-success" />
                  ) : (
                    <XCircle className="h-3.5 w-3.5 text-destructive" />
                  )}
                  <span className="text-[length:var(--text-sm)] font-medium">
                    {pipelineRunning
                      ? `Step ${pipelineJob.steps.length}/${pipelineJob.agents.length} — ${pipelineJob.steps.at(-1)?.agent ?? "starting…"}`
                      : pipelineJob.status === "done"
                        ? "Pipeline finished"
                        : "Pipeline exited with an error"}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-[length:var(--text-2xs)] text-muted-foreground">
                    ${pipelineTotalCost.toFixed(4)} so far
                  </span>
                  {!pipelineRunning && (
                    <Button variant="outline" size="sm" onClick={resetPipeline}>
                      <RotateCcw className="h-3 w-3" />
                      New run
                    </Button>
                  )}
                </div>
              </div>

              {/* live message box — only meaningful while a pipeline is still running */}
              {pipelineRunning && (
                <div className="mb-6 flex items-start gap-2">
                  <Textarea
                    value={liveMessage}
                    onChange={(e) => setLiveMessage(e.target.value)}
                    placeholder="Send a real message to the next step that hasn't launched yet…"
                    rows={2}
                    className="flex-1"
                  />
                  <Button size="sm" onClick={sendLiveMessage} disabled={!liveMessage.trim()}>
                    <Send className="h-3 w-3" />
                    Send
                  </Button>
                </div>
              )}
              {pipelineRunning && pipelineJob.pending_message && (
                <p className="-mt-4 mb-6 text-[length:var(--text-2xs)] text-brand">
                  Queued for the next step: &ldquo;{pipelineJob.pending_message}&rdquo;
                </p>
              )}

              {/* vertical, top-to-bottom step trace */}
              <div className="flex flex-col">
                {pipelineJob.steps.map((step, i) => {
                  const incoming = incomingEdgesFor(i, pipelineJob.steps, graphEdges);
                  return (
                    <div key={`${step.agent}-${i}`}>
                      {i > 0 && <div className="ml-[7px] h-4 w-px bg-border" />}
                      <motion.div
                        initial={{ opacity: 0, y: -8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.3, ease }}
                        className="rounded-lg border border-border bg-card px-4 py-3"
                      >
                        <div className="mb-2 flex items-center justify-between gap-2">
                          <span className="flex items-center gap-2">
                            <StatusIcon status={step.status} />
                            <span className="text-[length:var(--text-sm)] font-medium">{step.agent}</span>
                          </span>
                          <CostBadge cost={step.cost} turns={step.turns} />
                        </div>
                        {step.message && (
                          <p className="mb-2 text-[length:var(--text-2xs)] text-brand">
                            direct message: &ldquo;{step.message}&rdquo;
                          </p>
                        )}
                        <CommBadges edges={incoming} />
                        <OutputPane lines={step.output} />
                      </motion.div>
                    </div>
                  );
                })}

                {queuedAgents.map((agent, i) => (
                  <div key={agent}>
                    {(pipelineJob.steps.length > 0 || i > 0) && (
                      <div className="ml-[7px] h-4 w-px bg-border" />
                    )}
                    <div className="flex items-center gap-2 rounded-lg border border-dashed border-border px-4 py-2.5 opacity-50">
                      <Circle className="h-3.5 w-3.5 text-muted-foreground" />
                      <span className="text-[length:var(--text-sm)]">{agent}</span>
                      <span className="text-[length:var(--text-2xs)] text-muted-foreground">queued</span>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </TabsContent>

        {/* ================= SINGLE-AGENT MODE ================= */}
        <TabsContent value="single">
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
                      className="mb-3"
                    />
                  )}
                  <Textarea
                    value={singleMessage}
                    onChange={(e) => setSingleMessage(e.target.value)}
                    placeholder="Optional — a real direct message for this run (per CLAUDE.md's direct-chat rules, it's classified as a steer or a directive-level change before being acted on)"
                    rows={2}
                    disabled={isRunning}
                    className="mb-4"
                  />

                  <Button
                    onClick={() => setConfirming(true)}
                    disabled={(needsInput && !input.trim()) || isRunning}
                  >
                    {isRunning ? "Running…" : "Run"}
                  </Button>

                  {job && (
                    <div className="mt-6 border-t border-border pt-4">
                      <div className="mb-2.5 flex items-center justify-between gap-2">
                        <span className="flex items-center gap-2">
                          <StatusIcon status={job.status} />
                          <span className="text-[length:var(--text-2xs)] text-muted-foreground">
                            {job.status === "running"
                              ? "Real Claude Agent SDK call in progress"
                              : job.status === "done"
                                ? "Finished"
                                : "Exited with an error"}
                          </span>
                        </span>
                        <CostBadge cost={job.cost} turns={job.turns} />
                      </div>
                      {job.message && (
                        <p className="mb-2.5 text-[length:var(--text-2xs)] text-brand">
                          direct message: &ldquo;{job.message}&rdquo;
                        </p>
                      )}
                      <OutputPane lines={job.output} maxHeight={440} />
                    </div>
                  )}
                </motion.div>
              )}
            </div>
          </div>
        </TabsContent>
      </Tabs>

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

      <Dialog open={pipelineConfirming} onOpenChange={setPipelineConfirming}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <div className="flex items-center gap-2 text-warning">
              <AlertTriangle className="h-4 w-4" />
              <DialogTitle>Real spend, {selectedSteps.length}-step run</DialogTitle>
            </div>
            <DialogDescription className="pt-1 leading-[1.6]">
              This dispatches {selectedSteps.length} real, sequential Claude Agent SDK calls against
              live Cloudflare data — each step waits for the previous one to finish.{" "}
              {estimatedCost !== null
                ? `Estimated total from real history: ~$${estimatedCost.toFixed(2)}${
                    unknownStepCount > 0 ? ` (${unknownStepCount} step${unknownStepCount === 1 ? "" : "s"} with no history, not included)` : ""
                  }.`
                : "No prior runs for these steps — total cost is unknown."}{" "}
              Not reversible once started.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="bg-transparent border-none mx-0 mb-0 p-0 pt-2">
            <Button variant="outline" onClick={() => setPipelineConfirming(false)}>
              Cancel
            </Button>
            <Button onClick={launchPipeline}>Confirm &amp; run</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
