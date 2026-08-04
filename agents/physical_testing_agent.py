"""Physical Testing Agent — Verification & Validation division (CLAUDE.md).

Per CLAUDE.md: "test planning, execution, data analysis, and sim-vs-real
comparison. A mismatch sends the design back into the Concurrent
Engineering Cluster."

REAL DATA THIS IS TESTED AGAINST: execution, data analysis, and sim-vs-real
comparison are NOT possible yet — no physical article exists (this project
is still in the Fusion 360 model + docs phase per CLAUDE.md; an IRL build
is a later decision). But "test planning" is the first-listed, genuinely
separable half of this role, and it does NOT need a physical article to be
real: it needs real predicted values to plan tests AGAINST. Those already
exist — Simulation Agent's independently re-derived structural/aero numbers
and the real approved requirements. This agent drafts a real test plan
grounded in those real numbers, with real calculate()-derived pass/fail
thresholds, and explicitly refuses to fabricate execution, data, or a
sim-vs-real comparison that cannot happen without a built article.

Never fetches a hardcoded baseline id — see CLAUDE.md's Wave 4 review-pass
note (2026-08-02) on why that was a real bug in six other agents.
"""

from __future__ import annotations

import argparse
import json

import anyio
from claude_agent_sdk import create_sdk_mcp_server, tool

import agent_runtime
import agent_tools
import engineering_math
import storage

AGENT_NAME = "PhysicalTestingAgent"

MAX_TURNS = 40
TURN_WARNING_THRESHOLD = int(MAX_TURNS * 0.8)

VALID_STATUS = {"PLANNED", "BLOCKED"}


@tool("list_baselines", "List recent baselines, most recent first", {"limit": float})
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
    rows = storage.get_audit_log(limit=int(args.get("limit", 60) or 60), event_type=event_type)
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
    "record_test_plan_item",
    "Record ONE real planned physical test. status must be exactly 'PLANNED' "
    "(a real article-independent test that can be specified now) or 'BLOCKED' "
    "(genuinely cannot be specified without something that doesn't exist yet — "
    "say what, in blocked_reason).",
    {
        "test_name": str,
        "objective": str,
        "predicted_value_basis": str,
        "pass_fail_criteria": str,
        "equipment_needed": str,
        "status": str,
        "blocked_reason": str,
    },
)
async def record_test_plan_item_tool(args):
    status = args["status"].strip().upper()
    if status not in VALID_STATUS:
        return {
            "content": [{"type": "text", "text": f"[REJECTED] status must be one of {sorted(VALID_STATUS)}."}],
            "is_error": True,
        }
    if status == "PLANNED" and not args["pass_fail_criteria"].strip():
        return {
            "content": [
                {
                    "type": "text",
                    "text": "[REJECTED] a PLANNED test needs real, concrete pass_fail_criteria — a "
                    "test with no criteria isn't actually planned yet.",
                }
            ],
            "is_error": True,
        }
    if status == "BLOCKED" and not args["blocked_reason"].strip():
        return {
            "content": [{"type": "text", "text": "[REJECTED] a BLOCKED item needs a real blocked_reason."}],
            "is_error": True,
        }
    description = (
        f"TEST: {args['test_name']} | STATUS: {status} | OBJECTIVE: {args['objective']} | "
        f"PREDICTED_VALUE_BASIS: {args['predicted_value_basis']} | "
        f"PASS_FAIL: {args['pass_fail_criteria']} | EQUIPMENT: {args['equipment_needed']} | "
        f"BLOCKED_REASON: {args['blocked_reason']}"
    )
    storage.log_event(AGENT_NAME, "test_plan_item", description)
    return {"content": [{"type": "text", "text": f"Recorded {status} test: {args['test_name']}"}]}


log_event_tool = agent_tools.make_log_event_tool(AGENT_NAME)

ALLOWED_TOOLS = [
    "mcp__storage__calculate",
    "mcp__storage__search_kb",
    "mcp__storage__list_baselines",
    "mcp__storage__get_baseline",
    "mcp__storage__get_recent_events",
    "mcp__storage__list_requirements",
    "mcp__storage__record_test_plan_item",
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
        record_test_plan_item_tool,
        log_event_tool,
    ],
)

PROMPT = f"""You are the Physical Testing Agent for a multi-agent electric aircraft
project. CLAUDE.md's full role is "test planning, execution, data analysis,
and sim-vs-real comparison" — but execution, data analysis, and sim-vs-real
comparison are NOT possible yet, because no physical article exists (this
project is still in the Fusion 360 model + docs phase). Your real job THIS
RUN is the one genuinely separable half: draft a real, specific test plan
grounded in real predicted values, so it is ready the moment an article
exists — and explicitly refuse to fabricate the other three halves.

TURN BUDGET: you have a hard limit of {MAX_TURNS} conversation turns for this
ENTIRE task. If you are past turn {TURN_WARNING_THRESHOLD} and not done, stop
and record whatever real test-plan items you have — a smaller, real plan
beats an incomplete run.

ABSOLUTE RULE — NEVER DO ARITHMETIC YOURSELF:
Every predicted value or pass/fail threshold you cite must come from a
calculate call or be read directly from a real prior agent's stored output —
never worked out in your own reasoning text.

{engineering_math.format_formula_docs()}

Steps:
1. Call list_baselines, then get_baseline on the most recent one whose
   version starts "v0.1-config-draft" — never a hardcoded id, since the
   current baseline changes as the cluster re-derives it.
2. get_recent_events filtered to event_type="simulation_complete" (and any
   other real verification/adjudication event types you find referenced) to
   read Simulation Agent's real, independently-confirmed structural and
   aerodynamic numbers for the current design state. If no real simulation
   result exists yet for what a test would need, that test is BLOCKED, not
   guessable.
3. list_requirements(baseline_id=0) and identify which real, approved
   requirements a physical test could eventually verify (e.g. an altitude-
   hold tolerance, a structural safety margin, a battery C-rate/thermal
   limit).
4. For each real, article-independent test you can meaningfully specify now
   (e.g. static structural load test to the real spar safety factor,
   stall-speed flight-test envelope check against the real calculate()-
   derived V_stall, battery discharge/thermal test against the real pack
   spec), call record_test_plan_item with status="PLANNED": a concrete
   objective, the real predicted value and which real agent/calculate()
   result it comes from, concrete pass/fail criteria (e.g. "measured stall
   speed within +/-10% of the real predicted value"), and real equipment
   needed.
5. For anything that genuinely cannot be specified yet — because it depends
   on VTOL architecture, a component that doesn't exist, or a simulation
   result that hasn't been run — call record_test_plan_item with
   status="BLOCKED" and a real, specific blocked_reason. Do not invent a
   plausible test to avoid leaving something blocked.
6. Do NOT attempt execution, data analysis, or sim-vs-real comparison — say
   plainly in your final summary that these have nothing real to run against
   yet, rather than skipping the statement silently or fabricating a result.
7. Finish with ONE log_event, event_type="physical_testing_plan_complete",
   summarizing every PLANNED and BLOCKED item and what would unblock each
   blocked one.
"""


async def main():
    parser = argparse.ArgumentParser(
        description="Physical Testing Agent — real test-planning pass (execution genuinely blocked, no article exists)"
    )
    parser.add_argument("--message", help="A real message from Saiyam for this run (direct chat).")
    args = parser.parse_args()

    options = agent_runtime.build_options(
        system_prompt=(
            "You are the Physical Testing Agent from a multi-agent electric aircraft "
            "engineering project. Every predicted value must be traceable to a real "
            "calculate() result or a real prior agent's stored output — never fabricated."
        ),
        storage_server=storage_server,
        allowed_tools=ALLOWED_TOOLS,
        max_turns=MAX_TURNS,
    )
    stats = await agent_runtime.run_agent(AGENT_NAME, options, PROMPT, steer_message=args.message)
    print(f"\n===== DONE — cost ${stats['cost']:.4f} =====")


if __name__ == "__main__":
    anyio.run(main)
