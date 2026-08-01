import type {
  Baseline,
  Decision,
  KbEntry,
  LogEvent,
  Overview,
  RequirementsResponse,
  RosterAgent,
  RunJob,
  RunnableAgent,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:5001";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    throw new Error(payload.error ?? `${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  overview: () => get<Overview>("/api/overview"),
  roster: () => get<RosterAgent[]>("/api/roster"),
  decisions: () => get<Decision[]>("/api/decisions"),
  answerDecision: (question: string, answer: string) =>
    post<{ ok: true }>("/api/decisions/answer", { question, answer }),
  requirements: () => get<RequirementsResponse>("/api/requirements"),
  decideRequirement: (id: number, decision: "approved" | "rejected") =>
    post<{ ok: true }>(`/api/requirements/${id}`, { decision }),
  baselines: () => get<Baseline[]>("/api/baselines"),
  kb: (q: string) => get<KbEntry[]>(`/api/kb?q=${encodeURIComponent(q)}`),
  logs: (limit = 150) => get<LogEvent[]>(`/api/logs?limit=${limit}`),
  runnableAgents: () => get<RunnableAgent[]>("/api/agents/runnable"),
  startRun: (agent: string, input: string | null) =>
    post<{ job_id: string }>("/api/agents/run", { agent, input }),
  getRun: (jobId: string) => get<RunJob>(`/api/agents/run/${jobId}`),
};
