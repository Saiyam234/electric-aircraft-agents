"""Simulation Agent — Wave 3, Verification & Validation division (CLAUDE.md).

Per CLAUDE.md: "computational aerodynamic/structural simulation, plus
software verification (unit-testing the flight controller/autopilot code
itself — does it handle bad sensor input gracefully, does it fail safely)."

REAL DATA THIS IS TESTED AGAINST: whichever configuration baseline is most
recent at run time (never a hardcoded id — fixed 2026-08-02 after this
agent's own prompt was found still hardcoding baseline 89 by id, which would
have silently ignored baseline 210's later real re-derivation). First real
run (2026-07-31, against baseline 89): found the stored config still showed
ORIGINAL pre-review numbers (CL_max=1.1, V_stall=12.55 m/s) while Airframe
Engineer's real review (event 92) and Chief Integration's adjudication had
corrected those (CL_max=1.0, V_stall=13.16 m/s, spar allowable 400 MPa after
the requirement-29 hand-layup knockdown, safety factor ~8.6) — independently
re-derived the corrected numbers via calculate() from scratch and confirmed
they held up.

WHAT IT WILL NEED ONCE AVAILABLE: the "software verification" half —
unit-testing the flight controller/autopilot code for bad-input handling and
fail-safe behavior — genuinely cannot be done yet. No flight controller code
or spec exists; Software Engineer (also Wave 3) only produces an
architecture proposal, not deployable code, so there is nothing to unit-test
yet. This agent does not attempt to fabricate that half of its job.
"""

import argparse
import json

import anyio
from claude_agent_sdk import create_sdk_mcp_server, tool

import agent_runtime
import agent_tools
import engineering_math
import storage

AGENT_NAME = "SimulationAgent"

VALID_OUTCOMES = {"CONFIRMED", "DISCREPANCY_FOUND", "CANNOT_VERIFY"}


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
    "get_recent_events",
    "Read the N most recent audit-log events, optionally filtered by event_type "
    "(empty string = all types)",
    {"limit": float, "event_type": str},
)
async def get_recent_events_tool(args):
    event_type = (args.get("event_type") or "").strip() or None
    rows = storage.get_audit_log(limit=int(args.get("limit", 30) or 30), event_type=event_type)
    return {"content": [{"type": "text", "text": json.dumps(rows, default=str)}]}


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
    "report_verification",
    "Report the outcome of ONE independent re-derivation check. outcome must be "
    "exactly CONFIRMED, DISCREPANCY_FOUND, or CANNOT_VERIFY.",
    {
        "check": str,
        "outcome": str,
        "claimed_value": str,
        "independently_derived_value": str,
        "method": str,
    },
)
async def report_verification_tool(args):
    outcome = args["outcome"].strip().upper()
    if outcome not in VALID_OUTCOMES:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"[REJECTED] outcome must be one of {sorted(VALID_OUTCOMES)}, got "
                    f"{args['outcome']!r}. Independent verification means a real answer, not a hedge.",
                }
            ],
            "is_error": True,
        }
    if not args["method"].strip():
        return {
            "content": [
                {
                    "type": "text",
                    "text": "[REJECTED] method must describe the actual calculate() call(s) used — "
                    "a verification with no stated method cannot be trusted or reproduced.",
                }
            ],
            "is_error": True,
        }
    description = (
        f"CHECK: {args['check']} | OUTCOME: {outcome} | "
        f"CLAIMED: {args['claimed_value']} | INDEPENDENTLY_DERIVED: {args['independently_derived_value']} | "
        f"METHOD: {args['method']}"
    )
    storage.log_event(AGENT_NAME, "verification_result", description)
    if outcome == "DISCREPANCY_FOUND":
        storage.log_event(AGENT_NAME, "cluster_objection", description)
    return {"content": [{"type": "text", "text": f"Recorded {outcome} for check: {args['check'][:70]}"}]}


log_event_tool = agent_tools.make_log_event_tool(AGENT_NAME)

ALLOWED_TOOLS = [
    "mcp__storage__calculate",
    "mcp__storage__search_kb",
    "mcp__storage__list_baselines",
    "mcp__storage__get_baseline",
    "mcp__storage__get_recent_events",
    "mcp__storage__list_requirements",
    "mcp__storage__report_verification",
    "mcp__storage__log_event",
]

storage_server = create_sdk_mcp_server(
    name="storage",
    tools=[
        agent_tools.calculate_tool,
        agent_tools.search_kb_tool,
        list_baselines_tool,
        get_baseline_tool,
        get_recent_events_tool,
        list_requirements_tool,
        report_verification_tool,
        log_event_tool,
    ],
)

PROMPT = f"""You are the Simulation Agent for a multi-agent electric aircraft
project. Your real job right now is independent verification: re-derive the
Concurrent Engineering Cluster's own adjudicated structural and aerodynamic
numbers from scratch, using calculate(), and report whether they actually
hold — you are not allowed to just read a claimed number and agree with it.

ABSOLUTE RULE — NEVER DO ARITHMETIC YOURSELF:
Every number in your verification must come from a calculate call. If your
own mental arithmetic and a calculate() result would ever disagree, the
calculate() result is correct and your mental math is not to be reported.

{engineering_math.format_formula_docs()}

WHAT YOU CHECK — ALWAYS THE LATEST BASELINE, NEVER A HARDCODED ID:
Never assume a specific baseline id or a specific set of numbers is "the"
config — baseline ids and their stored numbers change as the cluster
re-derives them (e.g. baseline 89's original placeholder span vs. baseline
210's later re-derivation to the real decided 1.40 m target). Your job is a
real, repeatable capability: fetch whichever baseline is actually most
recent, independently re-derive ITS stored numbers from scratch via
calculate(), and report whether they actually hold up — you are not allowed
to just read a claimed number and agree with it.

Steps:
1. Call list_baselines, then get_baseline on the most recent one whose
   version starts "v0.1-config-draft". Read its real MTOW, wing area, and
   wingspan/semi-span.
2. get_recent_events filtered to event_type="airframe_review_complete" (and
   similarly for other cluster review event types you find referenced in the
   baseline's own log_event history) to see if a real structural/aero review
   exists for THIS baseline. If the baseline you fetched has no such review
   yet, or carries no real spar geometry (cap area, cap separation, load
   factor), say so plainly — do not borrow numbers from a different,
   older baseline's review to fill the gap.
3. Independently re-derive V_stall: calculate("stall_speed", ...) from the
   baseline's own stored mass, wing area, and CL_max. Compare your real
   result to whatever the baseline itself claims for stall speed.
4. If the baseline (or a real review event tied to it) states a load factor
   and wing semi-span, independently re-derive the root bending moment via
   calculate("wing_root_bending_moment", ...) and compare to its claimed
   value.
5. If real spar cap geometry (cap area, cap separation) exists for this
   baseline, independently re-derive bending stress via
   calculate("spar_cap_second_moment", ...) then calculate("bending_stress",
   ...), then calculate("safety_factor", ...) against the real allowable
   (checking whether the requirement-29 hand-layup knockdown was actually
   applied to that allowable, not assumed). If no real spar geometry exists
   yet, report CANNOT_VERIFY for this item and say exactly what's missing —
   do not invent placeholder geometry to get a number.
6. list_requirements(baseline_id=0) and confirm requirement 29 (hand-layup
   knockdown) is real and approved — do not take its existence on faith.
7. For each number you were able to check, call report_verification once
   with CONFIRMED if your independent result matches within reasonable
   rounding, DISCREPANCY_FOUND if it materially disagrees (state the real
   gap), or CANNOT_VERIFY if a genuinely required input is missing from this
   baseline (not as a way to avoid doing the math).
8. Finish with ONE log_event, event_type="simulation_complete", summarizing
   every outcome plus a plain statement that the "software verification"
   half of this role (unit-testing flight controller code) has nothing real
   to test against yet — no flight controller code or spec exists — so this
   run covers structural/aero verification only.
"""


async def main():
    argparse.ArgumentParser(
        description="Simulation Agent — independent re-derivation of the cluster's adjudicated numbers"
    ).parse_args()

    options = agent_runtime.build_options(
        system_prompt=PROMPT,
        storage_server=storage_server,
        allowed_tools=ALLOWED_TOOLS,
        max_turns=50,
    )
    stats = await agent_runtime.run_agent(AGENT_NAME, options, PROMPT)
    print(f"\n===== DONE — cost ${stats['cost']:.4f} =====")


if __name__ == "__main__":
    anyio.run(main)
