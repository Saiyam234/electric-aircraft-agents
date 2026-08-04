"""Chief Integration Agent (Concurrent Engineering Cluster, per CLAUDE.md).

Accepts, rejects, or modifies each proposal against the current configuration.

This is the agent that has to say no. Airframe and Propulsion each optimise
their own domain against the same configuration, and their answers routinely
conflict — a bigger battery closes the energy budget but raises MTOW, which
invalidates a spar sized at the old mass. Somebody has to adjudicate that
rather than merging both and hoping.

Per CLAUDE.md, every rejection is written to the lessons-learned layer so a
dead idea is never silently re-proposed later.

The decision field is validated in the tool, not merely requested in the
prompt: a decision outside ACCEPT/REJECT/MODIFY is refused. Same reasoning as
the Orchestrator's escalation categories — a rule the model could quietly
route around isn't a rule.

Usage:
    python3 -m agents.chief_integration_agent
"""

import argparse
import json

import anyio

import agent_runtime
import agent_tools
import engineering_math
import storage
from claude_agent_sdk import create_sdk_mcp_server, tool

AGENT_NAME = "ChiefIntegrationAgent"

VALID_DECISIONS = {"ACCEPT", "REJECT", "MODIFY"}


@tool("list_baselines", "List baselines to find the configuration being integrated against", {})
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


@tool("list_requirements", "List requirements — a proposal violating one of these cannot be accepted", {})
async def list_requirements_tool(args):
    return {"content": [{"type": "text", "text": json.dumps(storage.list_requirements(limit=100), default=str)}]}


@tool(
    "get_proposals",
    "Read the real proposals and objections raised by Airframe and Propulsion agents",
    {"limit": float},
)
async def get_proposals_tool(args):
    wanted = {"airframe_proposal", "propulsion_proposal", "cluster_objection", "configuration_validated"}
    rows = [e for e in storage.get_audit_log(limit=int(args["limit"])) if e["event_type"] in wanted]
    return {"content": [{"type": "text", "text": json.dumps(rows, default=str)}]}


@tool(
    "record_integration_decision",
    "Adjudicate ONE proposal. decision must be exactly ACCEPT, REJECT or MODIFY.",
    {"proposal_summary": str, "decision": str, "rationale": str, "modification": str},
)
async def record_integration_decision_tool(args):
    decision = args["decision"].strip().upper()
    if decision not in VALID_DECISIONS:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"[REJECTED] decision must be one of {sorted(VALID_DECISIONS)}, got {args['decision']!r}. "
                    "Every proposal must be genuinely adjudicated — there is no 'defer' or 'noted' option here.",
                }
            ],
            "is_error": True,
        }

    description = (
        f"DECISION: {decision} | PROPOSAL: {args['proposal_summary']} | "
        f"RATIONALE: {args['rationale']} | MODIFICATION: {args['modification'] or 'n/a'}"
    )
    storage.log_event(AGENT_NAME, "integration_decision", description)

    # CLAUDE.md: every rejection goes to the lessons-learned layer so a dead idea
    # is never re-proposed. A MODIFY records why the original form failed too.
    if decision in {"REJECT", "MODIFY"}:
        storage.log_event(
            AGENT_NAME,
            "lessons_learned",
            f"[{decision}] {args['proposal_summary']} — {args['rationale']}",
        )

    return {"content": [{"type": "text", "text": f"Recorded {decision} for: {args['proposal_summary'][:70]}"}]}


log_event_tool = agent_tools.make_log_event_tool(AGENT_NAME)

storage_server = create_sdk_mcp_server(
    name="storage",
    tools=[
        agent_tools.calculate_tool,
        agent_tools.search_kb_tool,
        list_baselines_tool,
        get_baseline_tool,
        list_requirements_tool,
        get_proposals_tool,
        record_integration_decision_tool,
        log_event_tool,
    ],
)

ALLOWED_TOOLS = [
    "mcp__storage__calculate",
    "mcp__storage__search_kb",
    "mcp__storage__list_baselines",
    "mcp__storage__get_baseline",
    "mcp__storage__list_requirements",
    "mcp__storage__get_proposals",
    "mcp__storage__record_integration_decision",
    "mcp__storage__log_event",
]

PROMPT = f"""You are the Chief Integration Agent for a multi-agent electric aircraft
engineering project. You accept, reject, or modify each proposal against the current
configuration. You are the agent that has to say no.

ABSOLUTE RULE — NEVER DO ARITHMETIC YOURSELF:
Every number you use to justify a decision must come from a calculate call. If you claim a
proposal breaks the mass budget or violates a limit, compute it — do not assert it.

AVAILABLE FORMULAS (exact parameter names required):
{engineering_math.format_formula_docs()}

Steps:
1. list_baselines, then get_baseline on the most recent "v0.1-config-draft" baseline. This
   is the configuration everything is being integrated against.
2. list_requirements. A proposal that violates a hard numeric requirement CANNOT be
   accepted — that is a hard gate, not a judgement call.
3. get_proposals (limit 60) to read the real proposals and objections that Airframe and
   Propulsion actually raised, plus Math & Physics' validation findings.
4. Adjudicate EVERY proposal with record_integration_decision. There is no defer option.

HOW TO ADJUDICATE — the whole point of this role:
Airframe and Propulsion each optimise their own domain against the same configuration, and
their answers frequently conflict without either being wrong on its own terms. Look
specifically for:
- MASS COUPLING: a proposal that grows mass invalidates anything sized at the old mass.
  If Propulsion grows the pack to close the energy budget, recompute whether Airframe's
  spar, the wing loading and the stall speed still hold at the new MTOW. Two proposals that
  are individually correct can be jointly inconsistent — that is exactly what you exist to
  catch.
- REQUIREMENT VIOLATIONS: check numeric proposals against the requirements. Anything that
  breaches one is a REJECT, regardless of how good the engineering reasoning was.
- ARCHITECTURE LEAKAGE: the VTOL architecture is deliberately not yet selected. A proposal
  that only works for one architecture, presented as if general, must be MODIFIED to state
  its dependency rather than accepted as-is.
- UNSUPPORTED NUMBERS: a proposal resting on an assumed figure where the knowledge base has
  a real cited one should be MODIFIED to use the real value.

Use ACCEPT only where the proposal is genuinely consistent with the configuration, the
requirements, and the other proposals. Use MODIFY when the idea is sound but its stated
form is wrong. Use REJECT when it cannot be made to work as proposed.

Do NOT manufacture disagreement to appear rigorous, and do NOT accept everything to avoid
conflict. Both are failures of this role. Judge what the evidence actually supports.

When done, call log_event ONCE with event_type="integration_review_complete" summarising
how many you accepted, rejected and modified, and which single conflict most needs Saiyam
or the Configuration Synthesis Lead to break the tie on.
"""


async def main():
    parser = argparse.ArgumentParser(description="Chief Integration Agent — adjudicate cluster proposals")
    parser.add_argument("--message", help="A real message from Saiyam for this run (direct chat).")
    args = parser.parse_args()

    options = agent_runtime.build_options(
        system_prompt=(
            "You are the Chief Integration Agent from a multi-agent electric aircraft "
            "engineering project. You never do arithmetic yourself — every number comes from "
            "a calculate call. You adjudicate honestly: neither rubber-stamping nor "
            "manufacturing objections. Be decisive and specific."
        ),
        storage_server=storage_server,
        allowed_tools=ALLOWED_TOOLS,
        max_turns=60,
    )

    stats = await agent_runtime.run_agent(AGENT_NAME, options, PROMPT, steer_message=args.message)
    print(f"\n===== DONE — cost ${stats['cost']:.4f} =====")


if __name__ == "__main__":
    anyio.run(main)
