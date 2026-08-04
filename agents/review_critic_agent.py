"""Review & Critic — Wave 4, Assurance Gate division (CLAUDE.md).

Per CLAUDE.md: "cross-system consistency and real-world usability audit.
Also periodically spot-checks direct-chat history against the log." One of
three genuinely separate, independent Assurance Gate offices — this agent
does not share tools, verdict logic, or prompts with Safety & Risk or
Regulatory.

REAL DATA THIS IS TESTED AGAINST RIGHT NOW: the full real Wave 1-3 audit
log (baseline drafting, Airframe/Propulsion review, Chief Integration's
adjudication, Innovation Validator, Simulation Agent's independent
verification, Software Engineer's proposals, Design Realization's script) —
a genuinely large body of real, cross-referenceable output to check for
internal consistency. Per an Orchestrator directive run for real on
2026-07-31, this office was independently assessed as PARTIALLY runnable
now: it can audit real cross-system consistency, but it is NOT a
baseline-clearing review, because no baseline is converged enough to clear.

WHAT IT WILL NEED ONCE AVAILABLE: a selected VTOL architecture (the 1.40 m
span re-derivation itself is done — baseline 210, 2026-08-02), at which
point this office's audit becomes a real precondition for Assurance sign-off
rather than a standalone consistency check. There is no real "direct-chat
history" to spot-check yet either — Saiyam has not messaged an agent
directly through a channel that logs as such — so that half of the role has
nothing to run against yet and this agent does not fabricate it.
"""

import argparse
import json

import anyio
from claude_agent_sdk import create_sdk_mcp_server, tool

import agent_runtime
import agent_tools
import storage

AGENT_NAME = "ReviewCritic"

VALID_OUTCOMES = {"CONSISTENT", "INCONSISTENCY_FOUND", "NEEDS_CLARIFICATION"}


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
    "record_consistency_check",
    "Record the outcome of ONE cross-system consistency check. outcome must be "
    "exactly CONSISTENT, INCONSISTENCY_FOUND, or NEEDS_CLARIFICATION.",
    {"check": str, "outcome": str, "systems_compared": str, "finding": str},
)
async def record_consistency_check_tool(args):
    outcome = args["outcome"].strip().upper()
    if outcome not in VALID_OUTCOMES:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"[REJECTED] outcome must be one of {sorted(VALID_OUTCOMES)}, got "
                    f"{args['outcome']!r}.",
                }
            ],
            "is_error": True,
        }
    if not args["systems_compared"].strip():
        return {
            "content": [
                {
                    "type": "text",
                    "text": "[REJECTED] systems_compared must name the real agents/events being "
                    "cross-checked — a consistency check against nothing named is not a check.",
                }
            ],
            "is_error": True,
        }
    description = (
        f"CHECK: {args['check']} | OUTCOME: {outcome} | "
        f"SYSTEMS_COMPARED: {args['systems_compared']} | FINDING: {args['finding']}"
    )
    storage.log_event(AGENT_NAME, "consistency_check", description)
    if outcome == "INCONSISTENCY_FOUND":
        storage.log_event(AGENT_NAME, "cluster_objection", description)
    return {"content": [{"type": "text", "text": f"Recorded {outcome} for check: {args['check'][:70]}"}]}


log_event_tool = agent_tools.make_log_event_tool(AGENT_NAME)

ALLOWED_TOOLS = [
    "mcp__storage__search_kb",
    "mcp__storage__list_baselines",
    "mcp__storage__get_baseline",
    "mcp__storage__get_recent_events",
    "mcp__storage__record_consistency_check",
    "mcp__storage__log_event",
]

storage_server = create_sdk_mcp_server(
    name="storage",
    tools=[
        agent_tools.search_kb_tool,
        list_baselines_tool,
        get_baseline_tool,
        get_recent_events_tool,
        record_consistency_check_tool,
        log_event_tool,
    ],
)

PROMPT = """You are the Review & Critic office of the Assurance Gate for a
multi-agent electric aircraft project — one of three genuinely separate,
independent offices (the other two are Safety & Risk and Regulatory). You do
not coordinate your verdict with them.

Your real job right now is NOT to clear a baseline — no baseline is
converged enough for that yet (VTOL architecture unselected). Your real job
is a scoped cross-system consistency audit: does what different real agents
actually said and did hang together, or does it quietly contradict itself?

You do not have a calculate tool. If you find yourself wanting to check
whether a number is numerically correct, that is Simulation Agent's job
(it already ran a real independent re-derivation) — your job is whether
DIFFERENT agents' real statements are consistent WITH EACH OTHER, not
whether any one number is right in isolation.

CRITICAL — NEVER HARDCODE A BASELINE ID OR A FIXED LIST OF PAST CLAIMS:
Baseline ids and what's genuinely current change over time (e.g. baseline
89's original placeholder span vs. baseline 210's later re-derivation to the
real 1.40 m target) — an earlier version of this prompt hardcoded
get_baseline(89) and a fixed set of Wave 1-3 checks, which would silently
audit stale claims instead of whatever is real right now. Always work from
what you actually read this run, not a memorized list.

Steps:
1. Call list_baselines, then get_baseline on the most recent one whose
   version starts "v0.1-config-draft", for the real current config.
2. get_recent_events with a generous limit (80+) and no type filter to read
   the real, actual sequence of what has happened so far — every real
   review, adjudication, verdict, and proposal on record. Read the real
   text, not a summary of it.
3. From what you actually read, identify genuine cross-references worth
   checking — cases where one agent's real claim depends on, restates, or
   should logically match another agent's real claim — and run each as a
   real cross-check via record_consistency_check. Examples of the kind of
   thing to look for (illustrative, not a fixed checklist to blindly
   repeat): does an independent numerical re-derivation actually match what
   an adjudication claims was accepted; does a generated artifact's stated
   caveats (e.g. a stale-span warning) actually match the real current state
   rather than a stale one; does one agent cite a concern that another
   agent's real review text does not actually support. Search the real
   event text for each side of every comparison — do not assume consistency
   and do not assume last run's specific findings still apply.
4. If you find a genuine gap, flag it as INCONSISTENCY_FOUND with the real
   quoted text from both sides. If everything genuinely lines up, say
   CONSISTENT plainly — a clean audit is a real, useful result, not a
   failure to find something.
5. There is no real direct-chat history to spot-check yet (no agent has
   been messaged directly through a channel that logs as such) — do not
   fabricate this half of your role. Say so plainly in your summary instead
   of skipping it silently.
6. Finish with ONE log_event, event_type="review_critic_complete",
   summarizing every check and its outcome, and stating plainly that this
   is a scoped consistency audit, not an Assurance Gate sign-off — no
   baseline has been stamped and this run does not stamp one.
"""


async def main():
    parser = argparse.ArgumentParser(
        description="Review & Critic — scoped cross-system consistency audit (Assurance Gate)"
    )
    parser.add_argument("--message", help="A real message from Saiyam for this run (direct chat).")
    args = parser.parse_args()

    options = agent_runtime.build_options(
        system_prompt=PROMPT,
        storage_server=storage_server,
        allowed_tools=ALLOWED_TOOLS,
        max_turns=50,
    )
    stats = await agent_runtime.run_agent(AGENT_NAME, options, PROMPT, steer_message=args.message)
    print(f"\n===== DONE — cost ${stats['cost']:.4f} =====")


if __name__ == "__main__":
    anyio.run(main)
