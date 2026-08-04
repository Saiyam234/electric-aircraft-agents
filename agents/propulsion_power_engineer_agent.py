"""Propulsion & Power Engineer (Concurrent Engineering Cluster, per CLAUDE.md).

Owns propulsion (motor selection, mounting, drivetrain), electrical power
(battery pack, wiring, BMS) and thermal (cooling/airflow).

Wave 2 scope: close the defect Math & Physics Engine actually found against
baseline 89 — the drafted pack delivers roughly 32 Wh usable against a 35 Wh
mission, so the sizing does not close on energy. That is this agent's problem
to solve, and solving it moves mass, which feeds back into hover power. The
loop has to be closed explicitly rather than assumed away.

Usage:
    python3 -m agents.propulsion_power_engineer_agent
"""

import argparse
import json

import anyio

import agent_runtime
import agent_tools
import engineering_math
import storage
from claude_agent_sdk import create_sdk_mcp_server, tool

AGENT_NAME = "PropulsionPowerEngineer"


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


@tool("list_requirements", "List requirements binding on propulsion and power", {})
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
    "propose_propulsion_decision",
    "Record one concrete propulsion/power/thermal proposal with its evidence and effect on the configuration",
    {"area": str, "proposal": str, "evidence": str, "effect_on_configuration": str},
)
async def propose_propulsion_decision_tool(args):
    description = (
        f"AREA: {args['area']} | PROPOSAL: {args['proposal']} | "
        f"EVIDENCE: {args['evidence']} | EFFECT: {args['effect_on_configuration']}"
    )
    storage.log_event(AGENT_NAME, "propulsion_proposal", description)
    return {"content": [{"type": "text", "text": f"Recorded propulsion proposal for area={args['area']}"}]}


@tool(
    "raise_objection",
    "Formally object to something in the current configuration the evidence does not support",
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
        propose_propulsion_decision_tool,
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
    "mcp__storage__propose_propulsion_decision",
    "mcp__storage__raise_objection",
    "mcp__storage__log_event",
]

PROMPT = f"""You are the Propulsion & Power Engineer for a multi-agent electric aircraft
engineering project. You own propulsion, electrical power, and thermal.

The aircraft is a 1:8-scale, electric, fully autonomous eVTOL. The VTOL architecture is NOT
yet selected, so treat rotor count and size as a variable to bracket, not a given.

ABSOLUTE RULE — NEVER DO ARITHMETIC YOURSELF:
Every number you report must come from a calculate call. If no formula fits, say so rather
than estimating.

AVAILABLE FORMULAS (exact parameter names required):
{engineering_math.format_formula_docs()}

Steps:
1. list_baselines, then get_baseline on the most recent "v0.1-config-draft" baseline.
2. get_recent_events (limit 30) and read the Math & Physics Engine's
   "configuration_validated" entry carefully. It found a specific, real defect — that is
   your starting point, not something to rediscover.
3. list_requirements — the LiPo voltage, thermal and charge-rate requirements are binding
   constraints on your design, not advice.
4. search_kb for real cited figures: battery pack specific energy, propeller and motor
   efficiency, rotor figure of merit, and LiPo discharge limits. Recent research added real
   sourced numbers for several of these — use them instead of the placeholder assumptions
   the configuration currently carries, and say explicitly where a real figure replaces an
   assumed one.

THE CENTRAL PROBLEM YOU MUST SOLVE:
Math & Physics found the drafted pack delivers roughly 32 Wh usable against a ~35 Wh
mission, so the configuration does not close on energy. Growing the pack adds mass; added
mass raises hover power; higher hover power demands more energy. Work that loop explicitly
with mission_energy_budget, hover_power, battery_pack_from_energy and energy_for_endurance
until it either converges on a consistent set of numbers or you can state clearly that it
does not converge at this MTOW. Either answer is acceptable; an unexamined guess is not.

Also address, with real calculations:
- C-RATE FEASIBILITY: use discharge_c_rate at hover power. Check the result against the
  knowledge base's LiPo guidance on sustained draw as a fraction of nameplate rating. If the
  pack cannot deliver hover current safely, that is a thermal-runaway path and a hard stop.
- THERMAL: relate your answer to the cell-temperature requirement. State what cooling
  provision, if any, the pack needs to stay inside it.
- ROTOR SIZING: bracket rotor diameter and count with disk_area_from_rotors and hover_power,
  and use rotor_tip_speed to check you have not proposed something that crosses into
  compressibility losses.

Record each concrete answer with propose_propulsion_decision. Where the configuration's
existing numbers are contradicted by real cited data, use raise_objection with the specific
replacement number — do not silently carry a placeholder forward, and do not invent
disagreement that the evidence does not support.

When done, call log_event ONCE with event_type="propulsion_review_complete" summarising
whether the energy loop closes, at what MTOW, and what remains blocked on the VTOL
architecture choice.
"""


async def main():
    parser = argparse.ArgumentParser(description="Propulsion & Power Engineer — energy closure pass")
    parser.add_argument("--message", help="A real message from Saiyam for this run (direct chat).")
    args = parser.parse_args()

    options = agent_runtime.build_options(
        system_prompt=(
            "You are the Propulsion & Power Engineer from a multi-agent electric aircraft "
            "engineering project. You never do arithmetic yourself — every number comes from "
            "a calculate call. Close loops explicitly rather than assuming them away."
        ),
        storage_server=storage_server,
        allowed_tools=ALLOWED_TOOLS,
        max_turns=60,
    )

    stats = await agent_runtime.run_agent(AGENT_NAME, options, PROMPT, steer_message=args.message)
    print(f"\n===== DONE — cost ${stats['cost']:.4f} =====")


if __name__ == "__main__":
    anyio.run(main)
