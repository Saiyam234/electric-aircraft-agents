"""Regulatory — Wave 4, Assurance Gate division (CLAUDE.md).

Per CLAUDE.md: "compliance review, including autonomous/uncrewed aircraft
rules (generally stricter than simple remote-control aircraft rules),
standard model-aircraft codes, and battery-handling rules." One of three
genuinely separate, independent Assurance Gate offices — this agent does not
share tools, verdict logic, or prompts with Safety & Risk. All three offices
must sign off independently before a baseline can be stamped.

REAL DATA THIS IS TESTED AGAINST RIGHT NOW: requirement #32 (regulatory
mass/dimensions, explicitly jurisdiction-neutral, states plainly that
"specific mass/altitude/registration thresholds will be pinned by the
Regulatory agent once a jurisdiction is chosen" — this agent's real,
current job), requirement #25 (LiPo cell temperature ceiling — a real
battery-handling constraint already approved), and baseline 89's real
MTOW (2.5 kg). Per an Orchestrator directive run for real on 2026-07-31
(job dispatched through the Run Console), Regulatory was independently
assessed as the one Wave 4 office that IS runnable now — architecture- and
span-agnostic at this MTOW, unlike Safety & Risk's full FMEA or
Manufacturing's BOM.

There is no existing KB coverage of real regulatory frameworks (no
Foundational Research sweep has covered this), so this agent gets real
WebSearch access — the same as Foundational Research Agent — rather than
asserting regulatory facts from training data, which could be stale or
simply wrong. Every regulatory claim must be a real, dated, cited source,
stored back into the KB so later agents don't have to re-research it.

WHAT IT WILL NEED ONCE AVAILABLE: an actual flight-test jurisdiction
(explicitly deferred — requirement #32 is written jurisdiction-neutral on
purpose). Until Saiyam picks one, this agent can only assess against the
GENERAL pattern across major jurisdictions (US/EU-style weight-tiered sUAS
categories), not a specific numeric threshold.
"""

import argparse
import json
import sys

import anyio
from claude_agent_sdk import create_sdk_mcp_server, tool

import agent_runtime
import agent_tools
import storage

AGENT_NAME = "Regulatory"

MAX_TURNS = 50
TURN_WARNING_THRESHOLD = int(MAX_TURNS * 0.8)

VALID_VERDICTS = {"COMPLIANT_LIKELY", "NEEDS_JURISDICTION_DECISION", "NON_COMPLIANT"}


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
    "list_requirements",
    "List formal requirements, optionally filtered by baseline_id (0 = all)",
    {"baseline_id": float},
)
async def list_requirements_tool(args):
    bid = int(args.get("baseline_id", 0) or 0)
    rows = storage.list_requirements(baseline_id=bid or None, limit=100)
    return {"content": [{"type": "text", "text": json.dumps(rows, default=str)}]}


@tool(
    "cite_regulatory_source",
    "Store a real regulatory fact in the Knowledge Base with a real citation. "
    "Never call this for a fact you are not confident is currently accurate and "
    "sourced from a real WebSearch result.",
    {"entry_id": str, "fact": str, "source_title": str, "source_url": str},
)
async def cite_regulatory_source_tool(args):
    try:
        result = storage.upsert_kb_checked(
            args["entry_id"],
            args["fact"],
            metadata={"source_title": args["source_title"], "source_url": args["source_url"]},
        )
    except ValueError as exc:
        return {"content": [{"type": "text", "text": f"[REJECTED] {exc}"}], "is_error": True}
    return {"content": [{"type": "text", "text": json.dumps(result, default=str)}]}


@tool(
    "record_compliance_verdict",
    "Record ONE compliance verdict on a specific real requirement or topic area. "
    "verdict must be exactly COMPLIANT_LIKELY, NEEDS_JURISDICTION_DECISION, or "
    "NON_COMPLIANT.",
    {"topic": str, "verdict": str, "citation": str, "rationale": str},
)
async def record_compliance_verdict_tool(args):
    verdict = args["verdict"].strip().upper()
    if verdict not in VALID_VERDICTS:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"[REJECTED] verdict must be one of {sorted(VALID_VERDICTS)}, got "
                    f"{args['verdict']!r}. A regulatory office does not hedge with a made-up category.",
                }
            ],
            "is_error": True,
        }
    if verdict == "COMPLIANT_LIKELY" and not args["citation"].strip():
        return {
            "content": [
                {
                    "type": "text",
                    "text": "[REJECTED] COMPLIANT_LIKELY requires a real citation — an uncited "
                    "compliance claim is exactly the failure mode this office exists to prevent.",
                }
            ],
            "is_error": True,
        }
    description = (
        f"TOPIC: {args['topic']} | VERDICT: {verdict} | "
        f"CITATION: {args['citation']} | RATIONALE: {args['rationale']}"
    )
    storage.log_event(AGENT_NAME, "regulatory_verdict", description)
    return {"content": [{"type": "text", "text": f"Recorded {verdict} for topic={args['topic']}"}]}


log_event_tool = agent_tools.make_log_event_tool(AGENT_NAME)

ALLOWED_TOOLS = [
    "WebSearch",
    "mcp__storage__search_kb",
    "mcp__storage__list_baselines",
    "mcp__storage__get_baseline",
    "mcp__storage__list_requirements",
    "mcp__storage__cite_regulatory_source",
    "mcp__storage__record_compliance_verdict",
    "mcp__storage__log_event",
]

storage_server = create_sdk_mcp_server(
    name="storage",
    tools=[
        agent_tools.search_kb_tool,
        list_baselines_tool,
        get_baseline_tool,
        list_requirements_tool,
        cite_regulatory_source_tool,
        record_compliance_verdict_tool,
        log_event_tool,
    ],
)

PROMPT = f"""You are the Regulatory office of the Assurance Gate for a multi-agent
electric aircraft project — one of three genuinely separate, independent
offices (the other two are Review & Critic and Safety & Risk). You do not
coordinate your verdict with them, and you never assume their sign-off
implies yours.

TURN BUDGET: you have a hard limit of {MAX_TURNS} conversation turns for
this ENTIRE task. Budget roughly: 60% real WebSearch + reading, 25% writing
citations and verdicts, 15% the final summary. If you are past turn
{TURN_WARNING_THRESHOLD} and not done, STOP researching and record verdicts
with whatever real evidence you have — a late, honest NEEDS_JURISDICTION_
DECISION beats an incomplete run.

ABSOLUTE RULE — NEVER ASSERT A REGULATORY FACT FROM TRAINING KNOWLEDGE ALONE:
Regulatory rules change and your training data has a cutoff. Before you cite
a specific numeric threshold, category name, or requirement, use WebSearch to
confirm it against a real, current source and call cite_regulatory_source so
the fact is stored with a real citation. A regulatory claim with no real
citation is worse than no claim.

Steps:
1. Call list_baselines, then get_baseline on the most recent one whose
   version starts "v0.1-config-draft" — never a hardcoded id, since the
   configuration baseline changes as the cluster re-derives it (e.g.
   baseline 89's old placeholder span vs. baseline 210's real 1.40 m
   re-derivation). Read the real MTOW you are assessing against.
2. list_requirements(baseline_id=0) and read requirement #32 (regulatory
   mass/dimensions, explicitly jurisdiction-neutral) and requirement #25
   (LiPo cell temperature ceiling) in full — these are the two real,
   approved requirements this office is directly responsible for.
3. search_kb first for any existing real regulatory research (there may be
   none — Foundational Research has not swept this topic yet). If nothing
   real exists, use WebSearch to find current, real sources on: (a) small
   uncrewed/autonomous aircraft weight-tiered regulatory categories in at
   least one major jurisdiction (state which — do not claim to cover all
   jurisdictions when requirement #32 is explicitly jurisdiction-neutral),
   (b) standard model-aircraft operating codes relevant to a 2.5 kg
   autonomous fixed-wing/VTOL platform, (c) lithium-polymer battery
   handling/transport/storage rules relevant to a hobby-scale project.
4. For each real source found, call cite_regulatory_source with a real
   entry_id, the real fact, and the real source title/URL — this grows the
   Knowledge Base for every future agent, not just you.
5. Call record_compliance_verdict once per real topic area you assessed
   (at minimum: general weight-tiered category fit at 2.5 kg MTOW; battery
   handling vs. requirement #25). Use COMPLIANT_LIKELY only with a real
   citation backing it. Use NEEDS_JURISDICTION_DECISION where the honest
   answer genuinely depends on which jurisdiction Saiyam eventually picks
   for flight testing — that is a legitimate, expected outcome given
   requirement #32's own design, not a cop-out.
6. Finish with ONE log_event, event_type="regulatory_review_complete",
   summarizing every verdict and stating plainly that full compliance
   confirmation is blocked on Saiyam choosing an actual flight-test
   jurisdiction, per requirement #32's own text.
"""


async def main():
    parser = argparse.ArgumentParser(
        description="Regulatory — compliance review pass (Assurance Gate)"
    )
    parser.add_argument("--message", help="A real message from Saiyam for this run (direct chat).")
    args = parser.parse_args()

    def on_turn(turn: int):
        if turn == TURN_WARNING_THRESHOLD:
            print(
                f"\n  ⚠️  {AGENT_NAME}: ~{turn} turns so far, approaching max_turns={MAX_TURNS}.",
                file=sys.stderr,
            )

    options = agent_runtime.build_options(
        system_prompt=PROMPT,
        storage_server=storage_server,
        allowed_tools=ALLOWED_TOOLS,
        builtin_tools=["WebSearch"],
        max_turns=MAX_TURNS,
    )
    stats = await agent_runtime.run_agent(AGENT_NAME, options, PROMPT, on_assistant_turn=on_turn, steer_message=args.message)
    print(f"\n===== DONE — cost ${stats['cost']:.4f} =====")


if __name__ == "__main__":
    anyio.run(main)
