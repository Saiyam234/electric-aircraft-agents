"""Math & Physics Engine (Concurrent Engineering Cluster, per CLAUDE.md).

Aerodynamic, structural and thermal calculation, plus flight-mechanics math.
Validates a drafted configuration: does the sizing actually close, or are the
numbers internally inconsistent?

DESIGN POINT — the arithmetic happens in Python, never in the model.

Language models are unreliable at multi-step numerical work, and a plausible-
looking wrong number is the worst possible output from the agent whose entire
job is being correct about numbers. The formulas live in engineering_math.py
(validated against published reference aircraft in test_engineering_math.py);
this agent decides WHICH calculation to run, supplies inputs, and interprets
results.

The formula documentation in the prompt is generated from the registry, so the
model can never be told a formula exists that doesn't, or miss one that does.

Usage:
    python3 -m agents.math_physics_engine_agent
"""

import argparse
import json

import anyio

import agent_runtime
import agent_tools
import engineering_math
import storage
from claude_agent_sdk import create_sdk_mcp_server, tool

AGENT_NAME = "MathPhysicsEngine"


@tool("list_baselines", "List baselines so you can pick the configuration to validate", {})
async def list_baselines_tool(args):
    return {"content": [{"type": "text", "text": json.dumps(storage.list_baselines(limit=50), default=str)}]}


@tool("get_baseline", "Fetch one baseline's full configuration by id", {"baseline_id": float})
async def get_baseline_tool(args):
    try:
        baseline = storage.get_baseline(int(args["baseline_id"]))
    except ValueError as exc:
        return {"content": [{"type": "text", "text": f"[REJECTED] {exc}"}], "is_error": True}
    return {"content": [{"type": "text", "text": json.dumps(baseline, default=str)}]}


@tool("list_requirements", "List requirements the configuration must satisfy", {})
async def list_requirements_tool(args):
    return {"content": [{"type": "text", "text": json.dumps(storage.list_requirements(limit=100), default=str)}]}


log_event_tool = agent_tools.make_log_event_tool(AGENT_NAME)

storage_server = create_sdk_mcp_server(
    name="storage",
    tools=[
        agent_tools.calculate_tool,
        list_baselines_tool,
        get_baseline_tool,
        list_requirements_tool,
        agent_tools.search_kb_tool,
        log_event_tool,
    ],
)

ALLOWED_TOOLS = [
    "mcp__storage__calculate",
    "mcp__storage__list_baselines",
    "mcp__storage__get_baseline",
    "mcp__storage__list_requirements",
    "mcp__storage__search_kb",
    "mcp__storage__log_event",
]

PROMPT = f"""You are the Math & Physics Engine for a multi-agent electric aircraft engineering
project. Your job is to check whether a drafted configuration's numbers hold up — does the
sizing close, or is it internally inconsistent?

The aircraft is a 1:8-scale, electric, fully autonomous eVTOL. The VTOL architecture is
deliberately not yet selected, so treat hover generically (total rotor disk area) rather than
assuming a specific arrangement.

ABSOLUTE RULE — NEVER DO ARITHMETIC YOURSELF:
Every number you report must come from a calculate call. Do not multiply, divide, or take a
square root in your reasoning text and present the result. If no formula fits, say so
explicitly rather than estimating. A confidently-stated wrong number is the worst thing you
can produce.

AVAILABLE FORMULAS (exact parameter names required):
{engineering_math.format_formula_docs()}

Steps:
1. list_baselines, then get_baseline on the most recent configuration draft (version starts
   "v0.1-config-draft"). If none exists, say so and stop — never invent a configuration.
2. list_requirements — some requirements carry hard numeric limits the configuration must
   satisfy. Check the configuration against them explicitly.
3. search_kb for the real coefficients you need (CL_max, CD0, Oswald efficiency, battery
   specific energy, LiPo discharge limits). State which value you used and its source. Where
   you must assume, label it an assumption clearly.
4. Work the configuration through calculate. Cover at minimum: wing loading, aspect ratio,
   stall speed, cruise Reynolds number, the full cruise solve, and hover power.

BEYOND JUST RE-CHECKING THE DRAFT — the following usually decide whether a small eVTOL
actually closes, and the draft may be silent on them. Investigate each and say what you find:
- HOVER DOMINANCE: use mission_energy_budget with a realistic hover time. Hover power
  typically dwarfs cruise power and quietly consumes the energy budget that endurance was
  sized around. Report hover's share of total energy.
- STRUCTURAL CLOSURE: use wing_root_bending_moment at a realistic manoeuvre/gust load factor
  (not 1.0), then spar_cap_second_moment, bending_stress and safety_factor. A wing spar
  failure is unrecoverable, so an inadequate margin here matters more than anything else
  you might find.
- C-RATE FEASIBILITY: use discharge_c_rate at hover power. A pack can hold enough energy and
  still be unable to deliver the current — that is a thermal-runaway path, and the knowledge
  base has the relevant LiPo limits.
- STABILITY: if the draft gives component masses/positions, use center_of_gravity and
  static_margin. If it doesn't, say that weight & balance cannot yet be checked.
- ROTOR TIP MACH: if rotor sizes are proposed, check rotor_tip_speed — small high-RPM rotors
  can quietly cross into compressibility losses.
- POWER-OFF BEHAVIOUR: best_glide_speed matters for failsafe planning under the autonomy
  requirements.

Where an input you need genuinely doesn't exist yet, compute across a bracketed RANGE of
plausible values and report how much the answer swings. A number that varies 5x across the
plausible range is itself the finding.

When done, call log_event ONCE with event_type="configuration_validated" summarizing what
checked out, what didn't, and the single biggest risk to the sizing closing. Then give a
clear written verdict: does this configuration close, and what specifically must change?
"""


async def main():
    argparse.ArgumentParser(description="Math & Physics Engine — configuration validation pass").parse_args()

    options = agent_runtime.build_options(
        system_prompt=(
            "You are the Math & Physics Engine from a multi-agent electric aircraft "
            "engineering project. You never do arithmetic yourself — every number comes "
            "from a calculate tool call. State assumptions explicitly. Be precise."
        ),
        storage_server=storage_server,
        allowed_tools=ALLOWED_TOOLS,
        max_turns=60,
    )

    stats = await agent_runtime.run_agent(AGENT_NAME, options, PROMPT)
    print(f"\n===== DONE — cost ${stats['cost']:.4f} =====")


if __name__ == "__main__":
    anyio.run(main)
