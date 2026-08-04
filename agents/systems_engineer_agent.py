"""Systems Engineer (Concurrent Engineering Cluster, per CLAUDE.md).

Wave 1 scope: requirements definition and traceability — derive formal,
verifiable requirements from the project's hard constraints, grounded in real
knowledge-base evidence rather than assumption.

Deliberately NOT in scope yet (the rest of this agent's CLAUDE.md role):
interface/message-schema ownership, integration test planning, and EMI/EMC.
Those need a configuration and real hardware choices to exist first.

Hard rule from CLAUDE.md, enforced here: this agent PROPOSES requirements,
never imposes them. Everything it writes lands with status 'proposed' and
carries an impact assessment for Saiyam to approve or reject. It never
changes an existing requirement's status itself.

Usage:
    python3 -m agents.systems_engineer_agent
"""

import argparse
import json

import anyio

import agent_runtime
import storage
from claude_agent_sdk import create_sdk_mcp_server, tool

AGENT_NAME = "SystemsEngineer"

# Verbatim from CLAUDE.md's "Current hard constraints". Requirements must trace
# back to these — and must NOT quietly resolve anything marked open/undecided.
HARD_CONSTRAINTS = """\
- Scale: 1:8, modeled in Fusion 360 at the true dimensions of that scale (no
  separate "scale down" step in CAD).
- Propulsion: electric.
- Takeoff/landing: eVTOL — vertical takeoff and landing is REQUIRED. But the
  VTOL ARCHITECTURE (tiltrotor / tiltwing / lift+cruise / tailsitter / other)
  is explicitly UNDECIDED and reserved for the engineering agents to discover.
- Flight autonomy: fully autonomous, no remote pilot. Current build target is
  flight-control-level autonomy (follows a pre-set waypoint plan on its own,
  like a standard autopilot). Mission-level autonomy is an explicit later step.
- Human override / kill-switch capability: STILL OPEN, undecided.
- Current deliverable: Fusion 360 model + engineering docs + research papers.
- Fabrication: solo build, resources still undetermined.
"""


@tool("search_kb", "Semantic search the knowledge base for evidence to ground a requirement", {"query": str})
async def search_kb_tool(args):
    matches = storage.search_kb(args["query"], top_k=5)
    trimmed = [
        {
            "id": m["id"],
            "text": m["metadata"].get("text", ""),
            "source_title": m["metadata"].get("source_title", ""),
            "source_url": m["metadata"].get("source_url", ""),
        }
        for m in matches
    ]
    return {"content": [{"type": "text", "text": json.dumps(trimmed, default=str)}]}


@tool("list_requirements", "List requirements already recorded, to avoid duplicating one", {})
async def list_requirements_tool(args):
    rows = storage.list_requirements(limit=100)
    return {"content": [{"type": "text", "text": json.dumps(rows, default=str)}]}


@tool(
    "propose_requirement",
    "Propose ONE formal requirement. Lands as 'proposed' for Saiyam to approve — never auto-approved.",
    {"text": str, "impact_assessment": str},
)
async def propose_requirement_tool(args):
    try:
        req_id = storage.add_requirement(args["text"], impact_assessment=args["impact_assessment"])
    except ValueError as exc:
        return {
            "content": [{"type": "text", "text": f"[REJECTED] requirement not stored: {exc}"}],
            "is_error": True,
        }
    return {"content": [{"type": "text", "text": f"Proposed requirement id={req_id} (status=proposed)"}]}


@tool("log_event", "Log a summary event to the audit log", {"event_type": str, "description": str})
async def log_event_tool(args):
    storage.log_event(AGENT_NAME, args["event_type"], args["description"])
    return {"content": [{"type": "text", "text": "Logged event"}]}


storage_server = create_sdk_mcp_server(
    name="storage",
    tools=[search_kb_tool, list_requirements_tool, propose_requirement_tool, log_event_tool],
)

ALLOWED_TOOLS = [
    "mcp__storage__search_kb",
    "mcp__storage__list_requirements",
    "mcp__storage__propose_requirement",
    "mcp__storage__log_event",
]

PROMPT = f"""You are the Systems Engineer for a multi-agent electric aircraft engineering
project. Your job right now is requirements definition: turn the project's hard constraints
into formal, verifiable requirements that the engineering agents can actually design against
and later test against.

THE PROJECT'S HARD CONSTRAINTS (these are given — you derive FROM them, you never change them):
{HARD_CONSTRAINTS}

Steps:
1. Call list_requirements first to see what already exists. Do not propose a duplicate or a
   trivial reword of an existing requirement.
2. For each area you intend to write a requirement about, call search_kb to find real
   evidence with concrete numbers. The knowledge base holds cited research on battery
   safety/limits, aerodynamics, and structural materials. Use it — a requirement with a real
   number behind it is worth far more than a vague one.
3. Propose roughly 8-14 requirements via propose_requirement, one call each. Prioritize the
   ones that genuinely constrain the design over exhaustive coverage.

WHAT MAKES A GOOD REQUIREMENT HERE:
- Written as "The aircraft shall ..." or "The <subsystem> shall ...".
- VERIFIABLE: someone must be able to test or measure whether it's met. "The aircraft shall
  be safe" is useless. "The battery pack shall not exceed 80 C cell surface temperature
  during any flight phase" is verifiable.
- Includes a concrete number wherever the evidence supports one, with that number traceable
  to knowledge-base evidence or directly to a hard constraint.
- The impact_assessment argument must explain: what this requirement constrains, why that
  number/limit, and what it would cost or break to change it later. This is what Saiyam
  reads when deciding whether to approve.

CRITICAL RULES:
- Do NOT write any requirement that silently decides something marked UNDECIDED above. In
  particular: nothing that assumes a specific VTOL architecture (no "the tilt mechanism
  shall...", no "the lift rotors shall..."), and nothing that assumes a human override /
  kill-switch either exists or doesn't. Requirements must hold true regardless of how those
  open questions land.
- Do NOT invent numbers. If the knowledge base doesn't support a specific figure and it
  doesn't follow from a hard constraint, either write the requirement without a fabricated
  number or state plainly in the impact_assessment that the threshold is still to be
  determined.
- You propose only. Everything lands as 'proposed' for Saiyam to approve.

When finished, call log_event ONCE with event_type="requirements_proposed" and a description
covering how many requirements you proposed, what areas they span, and any area where you
deliberately did NOT write a requirement because the evidence or a decision was missing.
Then give a short summary of what you proposed and why.
"""


async def main():
    parser = argparse.ArgumentParser(description="Systems Engineer — requirements definition pass")
    parser.add_argument("--message", help="A real message from Saiyam for this run (direct chat).")
    args = parser.parse_args()

    options = agent_runtime.build_options(
        system_prompt=(
            "You are the Systems Engineer from a multi-agent electric aircraft engineering "
            "project. You write verifiable, evidence-backed requirements and you propose "
            "them — you never impose them. Be precise and concrete."
        ),
        storage_server=storage_server,
        allowed_tools=ALLOWED_TOOLS,
        max_turns=40,
    )

    stats = await agent_runtime.run_agent(AGENT_NAME, options, PROMPT, steer_message=args.message)
    print(f"\n===== DONE — cost ${stats['cost']:.4f} =====")


if __name__ == "__main__":
    anyio.run(main)
