/**
 * The real pipeline structure from CLAUDE.md's "Agent roster" section — who
 * actually hands off to whom, not a guess. Kept separate from ROSTER (which
 * carries live build/run status) since this part is structural and doesn't
 * change with real-time data.
 *
 * Edges intentionally do NOT imply live inter-agent messaging exists — it
 * doesn't (see CLAUDE.md's "Still open" section: cluster messaging is a
 * sequential-script + shared-D1-state pattern today, not real-time
 * messaging). These edges are the intended handoff structure the roster is
 * built around.
 */
export const GRAPH_EDGES: [string, string][] = [
  ["Orchestrator", "Foundational Research Agent"],
  ["Orchestrator", "KB Manager"],
  ["Foundational Research Agent", "KB Manager"],
  ["KB Manager", "Systems Engineer"],
  ["KB Manager", "Innovation Validator"],
  ["Systems Engineer", "Configuration Synthesis Lead"],
  ["Configuration Synthesis Lead", "Airframe Engineer"],
  ["Configuration Synthesis Lead", "Propulsion & Power Engineer"],
  ["Configuration Synthesis Lead", "Math & Physics Engine"],
  ["Airframe Engineer", "Chief Integration Agent"],
  ["Propulsion & Power Engineer", "Chief Integration Agent"],
  ["Math & Physics Engine", "Chief Integration Agent"],
  ["Innovation Validator", "Chief Integration Agent"],
  ["Chief Integration Agent", "Software Engineer"],
  ["Chief Integration Agent", "Design Realization Agent"],
  ["Design Realization Agent", "Manufacturing Manager"],
  ["Software Engineer", "Simulation Agent"],
  ["Design Realization Agent", "Simulation Agent"],
  ["Simulation Agent", "Physical Testing Agent"],
  ["Physical Testing Agent", "Review & Critic"],
  ["Physical Testing Agent", "Safety & Risk"],
  ["Physical Testing Agent", "Regulatory"],
  ["Manufacturing Manager", "Review & Critic"],
  ["Review & Critic", "Literature Agent"],
  ["Safety & Risk", "Literature Agent"],
  ["Regulatory", "Literature Agent"],
];

export const DIVISION_COLOR: Record<string, string> = {
  Orchestrator: "var(--brand)",
  "Knowledge Base": "oklch(0.6 0.1 155)",
  Innovation: "oklch(0.65 0.12 70)",
  "Concurrent Engineering Cluster": "var(--brand)",
  Manufacturing: "oklch(0.6 0.08 300)",
  "Verification & Validation": "oklch(0.6 0.1 200)",
  "Assurance Gate": "oklch(0.6 0.15 25)",
  Literature: "oklch(0.55 0.05 90)",
};
