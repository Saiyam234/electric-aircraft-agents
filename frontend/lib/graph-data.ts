/**
 * Column order for the structured pipeline layout — matches CLAUDE.md's
 * "Agent roster" section ordering. Purely a layout concern (which column an
 * agent's division sits in); it does NOT determine which edges are drawn —
 * those come from real D1 provenance (backend/api.py's /api/agents/graph),
 * reconstructed from which agents' actual logged events referenced the same
 * real baseline/requirement, not from a prescribed diagram.
 */
export const DIVISION_ORDER: string[] = [
  "Orchestrator",
  "Knowledge Base",
  "Innovation",
  "Concurrent Engineering Cluster",
  "Manufacturing",
  "Verification & Validation",
  "Assurance Gate",
  "Literature",
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
