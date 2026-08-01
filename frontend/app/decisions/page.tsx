"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { api } from "@/lib/api";
import type { Decision } from "@/lib/types";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useCountsRefresh } from "@/lib/counts-context";
import { usePageSearch } from "@/lib/search-context";
import { CircleHelp } from "lucide-react";

const ease = [0.16, 1, 0.3, 1] as const;

export default function DecisionsPage() {
  const [decisions, setDecisions] = useState<Decision[] | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState<string | null>(null);
  const refresh = useCountsRefresh();
  const search = usePageSearch().toLowerCase();

  useEffect(() => {
    api.decisions().then(setDecisions).catch(() => setDecisions([]));
  }, []);

  const submit = async (question: string) => {
    const answer = (drafts[question] ?? "").trim();
    if (!answer) return;
    setSubmitting(question);
    try {
      await api.answerDecision(question, answer);
      setDecisions((prev) => (prev ?? []).filter((d) => d.question !== question));
      toast.success("Decision recorded", { description: answer.slice(0, 80) });
      refresh();
    } catch (e) {
      toast.error("Could not save your decision", { description: String(e) });
    } finally {
      setSubmitting(null);
    }
  };

  if (!decisions) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="h-4 w-80" />
        <Skeleton className="mt-6 h-40 w-full" />
      </div>
    );
  }

  const visible = decisions.filter(
    (d) => !search || d.question.toLowerCase().includes(search)
  );

  return (
    <div>
      <div className="mb-9">
        <h1 className="text-[length:var(--text-xl)] font-semibold tracking-[-0.02em]">Decisions</h1>
        <p className="mt-1.5 text-[length:var(--text-sm)] text-muted-foreground">
          Only you answer these — agents batch real forks here rather than deciding for themselves.
        </p>
      </div>

      {visible.length === 0 ? (
        <div className="flex flex-col items-center gap-2 rounded-lg bg-card px-5 py-16 text-center">
          <CircleHelp className="h-5 w-5 opacity-50" />
          <p className="text-[length:var(--text-xs)] text-muted-foreground">
            Nothing queued right now.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          <AnimatePresence initial={false}>
            {visible.map((d, i) => (
              <motion.div
                key={d.question}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, height: 0, marginBottom: 0 }}
                transition={{ duration: 0.3, delay: i * 0.03, ease }}
                className="rounded-lg border border-l-[3px] border-border border-l-brand bg-card p-5 shadow-sm"
              >
                <div className="mb-1.5 flex flex-wrap items-center gap-2 text-[length:var(--text-2xs)] text-muted-foreground">
                  <span>{d.agent}</span>
                  <span>{d.timestamp.slice(0, 19)}</span>
                </div>
                <p className="text-[length:var(--text-base)] font-medium leading-[1.5]">
                  {d.question}
                </p>
                {d.context && (
                  <p className="mt-2.5 text-[length:var(--text-xs)] leading-[1.6] text-muted-foreground">
                    {d.context}
                  </p>
                )}
                {d.options.length > 0 && (
                  <div className="mt-3.5 space-y-1.5">
                    {d.options.map((opt, oi) => (
                      <div
                        key={oi}
                        className="text-[length:var(--text-xs)] leading-[1.6] text-muted-foreground"
                      >
                        <span className="font-mono font-medium text-foreground">
                          {opt.option ?? opt.id ?? "•"}
                        </span>{" "}
                        {opt.label}
                      </div>
                    ))}
                  </div>
                )}
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    submit(d.question);
                  }}
                  className="mt-4 flex flex-wrap gap-2"
                >
                  <Input
                    value={drafts[d.question] ?? ""}
                    onChange={(e) =>
                      setDrafts((prev) => ({ ...prev, [d.question]: e.target.value }))
                    }
                    placeholder='Your decision — e.g. "Option F: set 1.40 m absolute"'
                    className="min-w-[260px] flex-1"
                  />
                  <Button
                    type="submit"
                    disabled={submitting === d.question || !(drafts[d.question] ?? "").trim()}
                  >
                    {submitting === d.question ? "Saving…" : "Submit"}
                  </Button>
                </form>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
