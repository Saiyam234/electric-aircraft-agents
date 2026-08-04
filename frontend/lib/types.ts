export interface StatusInfo {
  level: "ok" | "warn" | "bad";
  text: string;
}

export interface EscalationSummary {
  agent: string;
  timestamp: string;
  description: string;
}

export interface Overview {
  greeting: string;
  status: StatusInfo;
  total_cost: number;
  recent_cost_7d: number;
  spend_series: number[];
  total_runs: number;
  recent_runs_7d: number;
  run_series: number[];
  success_rate: number | null;
  known_run_count: number;
  avg_runtime_seconds: number | null;
  timed_run_count: number;
  agents_built: number;
  roster_total: number;
  open_decisions_count: number;
  escalations_count: number;
  proposed_requirements_count: number;
  kb_count: number | null;
  baselines_count: number;
  escalations: EscalationSummary[];
}

export type AgentStatus = "clean" | "error" | "turn_limit" | "not_run" | "not_built";

export interface RosterAgent {
  division: string;
  name: string;
  built: boolean;
  status: AgentStatus;
  run_count: number;
  error_count: number;
  unknown_count: number;
  latest_output: string | null;
  latest_output_type: string | null;
}

export interface AgentGraphNode {
  division: string;
  name: string;
  built: boolean;
}

export interface AgentGraphEdge {
  source: string;
  target: string;
  artifacts: string[];
}

export interface AgentGraphResponse {
  nodes: AgentGraphNode[];
  edges: AgentGraphEdge[];
}

export interface DecisionOption {
  option?: string;
  id?: string;
  label: string;
}

export interface Decision {
  agent: string;
  timestamp: string;
  question: string;
  context: string | null;
  options: DecisionOption[];
}

export interface Requirement {
  id: number;
  text: string;
  status: string;
  created_at: string;
  impact_assessment?: string | null;
}

export interface RequirementsResponse {
  status_counts: Record<string, number>;
  proposed: Requirement[];
}

export interface Baseline {
  id: number;
  version: string;
  status: string;
  created_at: string;
  stamped: boolean;
}

export interface KbEntry {
  id: string;
  text: string;
  score: number | null;
}

export interface LogEvent {
  agent: string;
  event_type: string;
  timestamp: string;
  description: string;
}

export type RunMode = "directive" | "topic" | "innovation" | "none";

export interface RunnableAgent {
  agent: string;
  mode: RunMode;
  run_count: number;
  avg_cost: number | null;
  min_cost: number | null;
  max_cost: number | null;
}

export interface RunJob {
  id: string;
  kind: "single";
  agent: string;
  module: string;
  mode: RunMode;
  input: string | null;
  message: string | null;
  status: "running" | "done" | "error";
  output: string[];
  started_at: number;
  finished_at: number | null;
  exit_code: number | null;
  pid: number | null;
  cost: number | null;
  turns: number | null;
}

export interface PipelineStep {
  agent: string;
  module: string;
  message: string | null;
  status: "running" | "done" | "error";
  output: string[];
  started_at: number;
  finished_at: number | null;
  exit_code: number | null;
  cost: number | null;
  turns: number | null;
}

export interface PipelineJob {
  id: string;
  kind: "pipeline";
  agent: "Pipeline";
  agents: string[];
  status: "running" | "done" | "error";
  steps: PipelineStep[];
  current_step: number;
  pending_message: string | null;
  started_at: number;
  finished_at: number | null;
}

export type RunJobOrPipeline = RunJob | PipelineJob;

export interface PipelineStepCost {
  agent: string;
  mode: RunMode;
  run_count: number;
  avg_cost: number | null;
  min_cost: number | null;
  max_cost: number | null;
}

export interface PipelineInfo {
  order: string[];
  steps: PipelineStepCost[];
  estimated_total_cost: number | null;
  steps_with_no_history: number;
}
