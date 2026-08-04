"""Airframe Engineer (Concurrent Engineering Cluster, per CLAUDE.md).

Owns aerodynamics, structures, mechanical systems (landing gear, linkages,
actuation), and materials selection.

Wave 2 scope: take the real configuration Configuration Synthesis Lead
drafted and the real defects Math & Physics Engine found against it, and
propose concrete airframe answers — airfoil selection at the actual cruise
Reynolds number, a spar that closes structurally at a real load factor, and
a materials/layup approach buildable by one person.

This agent is expected to DISAGREE where the evidence supports it. Wave 1
produced a configuration nobody challenged, because nobody existed to
challenge it. That is this agent's job.

Usage:
    python3 -m agents.airframe_engineer_agent
"""

import argparse
import json

import anyio

import agent_runtime
import agent_tools
import engineering_math
import storage
from claude_agent_sdk import create_sdk_mcp_server, tool

AGENT_NAME = "AirframeEngineer"


@tool("list_baselines", "List baselines to find the configuration to work from", {})
async def list_baselines_tool(args):
    return {"content": [{"type": "text", "text": json.dumps(storage.list_baselines(limit=50), default=str)}]}


@tool("get_baseline", "Fetch one baseline's full configuration by id", {"baseline_id": float})
async def get_baseline_tool(args):
    try:
        return {
            "content": [
                {"type": "text", "text": json.dumps(storage.get_baseline(int(args["baseline_id"])), default=str)}
            ]
        }
    except ValueError as exc:
        return {"content": [{"type": "text", "text": f"[REJECTED] {exc}"}], "is_error": True}


@tool("list_requirements", "List requirements the airframe must satisfy", {})
async def list_requirements_tool(args):
    return {"content": [{"type": "text", "text": json.dumps(storage.list_requirements(limit=100), default=str)}]}


@tool(
    "get_recent_events",
    "Read recent audit events — use this to find Math & Physics Engine's validation findings",
    {"limit": float},
)
async def get_recent_events_tool(args):
    return {
        "content": [{"type": "text", "text": json.dumps(storage.get_audit_log(limit=int(args["limit"])), default=str)}]
    }


@tool(
    "propose_airframe_decision",
    "Record one concrete airframe proposal (airfoil, spar, material, mechanism) with its evidence and its effect on the configuration",
    {"area": str, "proposal": str, "evidence": str, "effect_on_configuration": str},
)
async def propose_airframe_decision_tool(args):
    description = (
        f"AREA: {args['area']} | PROPOSAL: {args['proposal']} | "
        f"EVIDENCE: {args['evidence']} | EFFECT: {args['effect_on_configuration']}"
    )
    storage.log_event(AGENT_NAME, "airframe_proposal", description)
    return {"content": [{"type": "text", "text": f"Recorded airframe proposal for area={args['area']}"}]}


@tool(
    "raise_objection",
    "Formally object to something in the current configuration that the evidence does not support",
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

storage_server = create_sdk_mcp_server(
    name="storage",
    tools=[
        agent_tools.calculate_tool,
        agent_tools.search_kb_tool,
        list_baselines_tool,
        get_baseline_tool,
        list_requirements_tool,
        get_recent_events_tool,
        propose_airframe_decision_tool,
        raise_objection_tool,
        log_event_tool,
    ],
)

ALLOWED_TOOLS = [
    "mcp__storage__calculate",
    "mcp__storage__search_kb",
    "mcp__storage__list_baselines",
    "mcp__storage__get_baseline",
    "mcp__storage__list_requirements",
    "mcp__storage__get_recent_events",
    "mcp__storage__propose_airframe_decision",
    "mcp__storage__raise_objection",
    "mcp__storage__log_event",
]

PROMPT = f"""You are the Airframe Engineer for a multi-agent electric aircraft engineering
project. You own aerodynamics, structures, mechanical systems, and materials selection.

The aircraft is a 1:8-scale, electric, fully autonomous eVTOL. The VTOL architecture is
NOT yet selected — do not assume one, and do not propose anything that only works for a
single architecture without saying so explicitly.

ABSOLUTE RULE — NEVER DO ARITHMETIC YOURSELF:
Every number you report must come from a calculate call. Do not multiply, divide, or take a
square root in your reasoning and present the result. If no formula fits, say so rather than
estimating.

AVAILABLE FORMULAS (exact parameter names required):
{engineering_math.format_formula_docs()}

Steps:
1. list_baselines, then get_baseline on the most recent "v0.1-config-draft" baseline. This
   is real prior work by the Configuration Synthesis Lead — read it properly.
2. get_recent_events (limit 30) and find the Math & Physics Engine's
   "configuration_validated" entry. It already identified specific defects. Read them; do
   not rediscover them from scratch, and do not contradict them without recomputing.
3. list_requirements — several carry hard numeric limits binding on the airframe,
   particularly the composite laminate ply rules.
4. search_kb for real evidence on airfoils at the actual cruise Reynolds number, composite
   layup schedules, spar construction, and material allowables. The knowledge base has cited
   research on all of these — use the real numbers, do not recall them.

YOUR JOB — produce concrete airframe answers, not observations:
- AIRFOIL: the configuration currently carries an assumed CL_max with no airfoil behind it.
  Recompute the cruise Reynolds number, then select a specific airfoil suited to that regime
  and say what CL_max and CD0 it actually supports. If the real values differ from what the
  configuration assumed, that changes stall speed and cruise power — recompute both and say
  so plainly.
- STRUCTURE: size a real spar. Use wing_root_bending_moment at a defensible manoeuvre load
  factor (state which and why), then spar_cap_second_moment, bending_stress and
  safety_factor against a materials allowable you justify from the knowledge base. Also
  check stiffness with cantilever_tip_deflection — a spar can pass on strength and still
  flex too much for control surfaces or rotor clearance.
- MATERIALS AND BUILDABILITY: propose a layup that satisfies the ply-orientation
  requirements AND is achievable by one person with hand layup and vacuum bagging. A
  schedule that needs an autoclave is not a real answer for this project.

Record each concrete answer with propose_airframe_decision.

CHALLENGE THE CONFIGURATION — this is the point of you existing:
Wave 1's configuration was drafted with no other engineer to argue with it, so its
assumptions went untested. Where the evidence genuinely contradicts it, use raise_objection
with a specific proposed change. Do not manufacture disagreement to seem rigorous — but do
not rubber-stamp assumed values that real airfoil or material data does not support. An
assumption that survives your check should be stated as now-verified; one that doesn't
should be objected to with the number that replaces it.

When done, call log_event ONCE with event_type="airframe_review_complete" summarising your
decisions, your objections, and what you could not resolve without the VTOL architecture.
"""


async def main():
    parser = argparse.ArgumentParser(description="Airframe Engineer — airfoil, structures and materials pass")
    parser.add_argument("--message", help="A real message from Saiyam for this run (direct chat).")
    args = parser.parse_args()

    options = agent_runtime.build_options(
        system_prompt=(
            "You are the Airframe Engineer from a multi-agent electric aircraft engineering "
            "project. You never do arithmetic yourself — every number comes from a calculate "
            "call. You challenge unsupported assumptions rather than accepting them. Be precise."
        ),
        storage_server=storage_server,
        allowed_tools=ALLOWED_TOOLS,
        max_turns=60,
    )

    stats = await agent_runtime.run_agent(AGENT_NAME, options, PROMPT, steer_message=args.message)
    print(f"\n===== DONE — cost ${stats['cost']:.4f} =====")


if __name__ == "__main__":
    anyio.run(main)
