"""Software Engineer — Wave 3, Concurrent Engineering Cluster (CLAUDE.md).

Per CLAUDE.md: "flight controller, telemetry, cockpit/UI, autonomous
navigation/guidance logic, autopilot implementation (the executable side of
flight controls — Math & Physics Engine owns the calculation side), and
ground control/override station software if a human override capability is
confirmed."

REAL DATA THIS IS TESTED AGAINST RIGHT NOW: CLAUDE.md's decided autonomy
level (flight-control-only — follows a pre-set flight plan/waypoints, no
open-ended decision-making yet), the real approved EMI/EMC requirement
(#31, motor wiring/ESC/antenna routing vs. GPS and telemetry susceptibility),
and real cited Knowledge Base evidence from Foundational Research's actual
transition-control research. Human override / kill-switch capability is
still explicitly undecided in CLAUDE.md, so ground-override-station software
is out of scope for this run.

WHAT IT WILL NEED ONCE AVAILABLE: VTOL architecture is still not selected
(CLAUDE.md — explicitly reserved for the cluster, not to be defaulted). The
hover-to-cruise TRANSITION control logic is fundamentally different for a
tailsitter (full attitude rotation through the post-stall regime) versus a
tiltrotor/tiltwing/lift+cruise — so this agent cannot honestly design
transition control yet. This run proposes only the architecture-agnostic
parts of the flight-control stack and explicitly flags transition control as
blocked, the same way Configuration Synthesis Lead flags architecture-
dependent geometry as not yet decided.
"""

import argparse
import json

import anyio
from claude_agent_sdk import create_sdk_mcp_server, tool

import agent_runtime
import agent_tools
import engineering_math
import storage

AGENT_NAME = "SoftwareEngineer"


@tool("list_baselines", "List recent baselines", {"limit": float})
async def list_baselines_tool(args):
    rows = storage.list_baselines(limit=int(args.get("limit", 10) or 10))
    return {"content": [{"type": "text", "text": json.dumps(rows, default=str)}]}


@tool("get_baseline", "Get one baseline's full config by id", {"baseline_id": float})
async def get_baseline_tool(args):
    try:
        row = storage.get_baseline(int(args["baseline_id"]))
    except ValueError as exc:
        return {"content": [{"type": "text", "text": f"[REJECTED] {exc}"}], "is_error": True}
    return {"content": [{"type": "text", "text": json.dumps(row, default=str)}]}


@tool(
    "list_requirements",
    "List formal requirements, optionally filtered by baseline_id (0 = all)",
    {"baseline_id": float},
)
async def list_requirements_tool(args):
    bid = int(args.get("baseline_id", 0) or 0)
    rows = storage.list_requirements(baseline_id=bid or None, limit=100)
    return {"content": [{"type": "text", "text": json.dumps(rows, default=str)}]}


@tool(
    "propose_software_decision",
    "Record one concrete flight-software proposal (control loop, state estimation, "
    "failsafe, EMI mitigation) with its evidence and what it depends on",
    {"area": str, "proposal": str, "evidence": str, "depends_on_architecture": str},
)
async def propose_software_decision_tool(args):
    description = (
        f"AREA: {args['area']} | PROPOSAL: {args['proposal']} | "
        f"EVIDENCE: {args['evidence']} | DEPENDS_ON_ARCHITECTURE: {args['depends_on_architecture']}"
    )
    storage.log_event(AGENT_NAME, "software_proposal", description)
    return {"content": [{"type": "text", "text": f"Recorded software proposal for area={args['area']}"}]}


@tool(
    "raise_objection",
    "Formally object to something in the current configuration or a prior proposal "
    "that the evidence does not support",
    {"target": str, "objection": str, "evidence": str, "proposed_change": str},
)
async def raise_objection_tool(args):
    description = (
        f"TARGET: {args['target']} | OBJECTION: {args['objection']} | "
        f"EVIDENCE: {args['evidence']} | PROPOSED CHANGE: {args['proposed_change']}"
    )
    storage.log_event(AGENT_NAME, "cluster_objection", description)
    return {"content": [{"type": "text", "text": f"Objection recorded against: {args['target']}"}]}


log_event_tool = agent_tools.make_log_event_tool(AGENT_NAME)

ALLOWED_TOOLS = [
    "mcp__storage__calculate",
    "mcp__storage__search_kb",
    "mcp__storage__list_baselines",
    "mcp__storage__get_baseline",
    "mcp__storage__list_requirements",
    "mcp__storage__propose_software_decision",
    "mcp__storage__raise_objection",
    "mcp__storage__log_event",
]

storage_server = create_sdk_mcp_server(
    name="storage",
    tools=[
        agent_tools.calculate_tool,
        agent_tools.search_kb_tool,
        list_baselines_tool,
        get_baseline_tool,
        list_requirements_tool,
        propose_software_decision_tool,
        raise_objection_tool,
        log_event_tool,
    ],
)

PROMPT = f"""You are the Software Engineer for a multi-agent electric aircraft
project — the executable side of flight controls. Math & Physics Engine owns
the calculation side; you own control-loop structure, state estimation,
telemetry, and failsafe logic.

ABSOLUTE RULE — NEVER DO ARITHMETIC YOURSELF:
If you need to cite a number (a control loop rate, a timeout, a real cruise
speed to design telemetry bandwidth around), it must come from a calculate
call or be read directly from a real stored baseline/requirement — never
estimated in your own reasoning.

{engineering_math.format_formula_docs()}

CRITICAL — DO NOT DESIGN HOVER-TO-CRUISE TRANSITION CONTROL:
VTOL architecture (tiltrotor, tiltwing, lift+cruise, tailsitter) is not yet
selected — that decision is explicitly reserved for the Concurrent
Engineering Cluster, not to be defaulted by you. Transition control is
fundamentally different per architecture (a tailsitter rotates through the
full post-stall angle-of-attack range; a lift+cruise aircraft never does).
Do NOT propose a specific transition-control algorithm. Instead, propose
only what is genuinely architecture-agnostic, and for anything that depends
on the architecture, say so explicitly in depends_on_architecture rather
than picking one to make progress.

CRITICAL — AUTONOMY LEVEL IS DECIDED, DON'T EXCEED IT:
CLAUDE.md's current build target is flight-control-only autonomy: the
aircraft follows a pre-set flight plan/waypoints on its own, like a standard
autopilot. Do not design open-ended decision-making logic (that is an
explicit long-term direction, not the current target). Human override / kill
switch capability is still undecided — do not assume it exists or design a
ground override station.

Steps:
1. list_baselines then get_baseline on the most recent real baseline (89) to
   see the real mission profile (2 min hover + 15 min cruise) and any
   locked aerodynamic numbers you should design telemetry/control-loop
   parameters around.
2. list_requirements(baseline_id=0) and read requirement #31 (EMI/EMC — motor
   wiring, ESC placement, antenna routing vs. GPS/telemetry susceptibility)
   in full. This is a real, approved requirement your architecture must
   actually address, not a box to check.
3. search_kb for real cited evidence on autonomous flight control
   architectures for small VTOL/fixed-wing UAVs (Foundational Research has
   already covered this) to ground your proposals in real precedent rather
   than generic autopilot knowledge.
4. Propose the architecture-agnostic parts of the flight-control stack via
   propose_software_decision — at minimum: (a) state estimation / sensor
   fusion approach for a small low-cost autonomous platform, (b) the
   waypoint-following control loop structure for the CRUISE phase (this part
   IS architecture-agnostic — fixed-wing cruise control is the same
   regardless of how the aircraft got into cruise), (c) a concrete EMI
   mitigation strategy that actually satisfies requirement #31, (d) a
   loss-of-GPS / loss-of-telemetry failsafe behavior. For each, use
   depends_on_architecture to state plainly whether hover-phase control and
   transition control are blocked pending VTOL architecture selection.
5. If you find a real gap — e.g. a requirement your proposals can't yet
   satisfy without an architecture decision — raise_objection rather than
   silently proposing something incomplete and calling it done.
6. Finish with ONE log_event, event_type="software_review_complete",
   summarizing what you proposed, what remains explicitly blocked on VTOL
   architecture selection, and why.
"""


async def main():
    argparse.ArgumentParser(
        description="Software Engineer — architecture-agnostic flight-software proposal pass"
    ).parse_args()

    options = agent_runtime.build_options(
        system_prompt=PROMPT,
        storage_server=storage_server,
        allowed_tools=ALLOWED_TOOLS,
        max_turns=60,
    )
    stats = await agent_runtime.run_agent(AGENT_NAME, options, PROMPT)
    print(f"\n===== DONE — cost ${stats['cost']:.4f} =====")


if __name__ == "__main__":
    anyio.run(main)
