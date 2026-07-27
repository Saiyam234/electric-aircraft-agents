"""Orchestrator agent (per CLAUDE.md).

Job: decompose Saiyam's directives into open design questions, track project
state (baseline versioning, schedule/budget risk), batch communication into
decision requests and milestone digests, and enforce the escalation rule —
safety/regulatory/irreversible-cost issues always surface immediately, never
batched, no exceptions.

This test covers three real scenarios in one run, using real project state
(actual audit log + baseline history already in D1) rather than fabricated
data:
1. Decompose one real directive into concrete open design questions.
2. Classify an incoming safety-concern message and confirm it escalates
   immediately rather than getting queued/batched.
3. Produce three real, distinct artifacts: a batched decision request, a
   milestone digest (built from real audit log + baseline history), and an
   immediate escalation.

Decision requests and digest items are logged to the audit log as they're
queued (event_type="decision_request" / "digest_item") — a structurally
different, non-immediate path from escalate_immediately, which is a
separate tool logging event_type="escalation". The distinction is
architectural, not just a text label: escalation bypasses the batching
tools entirely.
"""

import json
import anyio

import agent_runtime
import storage
from claude_agent_sdk import create_sdk_mcp_server, tool

ESCALATION_CATEGORIES = {"safety", "regulatory", "irreversible_cost"}


@tool("get_recent_events", "Fetch recent real audit log entries for project-state tracking", {"limit": float})
async def get_recent_events_tool(args):
    events = storage.get_audit_log(limit=int(args["limit"]))
    return {"content": [{"type": "text", "text": json.dumps(events, default=str)}]}


@tool("list_baselines", "List all real baselines currently in D1 (id, version, status, created_at)", {})
async def list_baselines_tool(args):
    baselines = storage.list_baselines()
    return {"content": [{"type": "text", "text": json.dumps(baselines, default=str)}]}


@tool("log_event", "Log a general Orchestrator event to the audit log", {"event_type": str, "description": str})
async def log_event_tool(args):
    storage.log_event("Orchestrator", args["event_type"], args["description"])
    return {"content": [{"type": "text", "text": "Logged event"}]}


@tool(
    "queue_decision_request",
    "Queue a decision request for Saiyam at a real fork — batched, NOT sent immediately",
    {"question": str, "context": str, "options_json": str},
)
async def queue_decision_request_tool(args):
    description = f"QUESTION: {args['question']} | CONTEXT: {args['context']} | OPTIONS: {args['options_json']}"
    storage.log_event("Orchestrator", "decision_request", description)
    return {"content": [{"type": "text", "text": "Queued as a batched decision request (not sent immediately)."}]}


@tool(
    "escalate_immediately",
    "Escalate safety/regulatory/irreversible-cost issues to Saiyam RIGHT NOW, bypassing all batching",
    {"category": str, "description": str},
)
async def escalate_immediately_tool(args):
    category = args["category"]
    if category not in ESCALATION_CATEGORIES:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"REJECTED: category must be one of {sorted(ESCALATION_CATEGORIES)}, got {category!r}. "
                    "This tool is only for the standing hard-rule categories — anything else goes through "
                    "queue_decision_request or queue_digest_item instead.",
                }
            ],
            "is_error": True,
        }
    storage.log_event("Orchestrator", "escalation", f"[{category.upper()}] {args['description']}")
    print(f"\n  🚨 ESCALATION LOGGED — category={category} — bypassing all batching, surfaced immediately 🚨\n")
    return {
        "content": [
            {
                "type": "text",
                "text": f"ESCALATED IMMEDIATELY (category={category}). This does not wait for a digest or decision batch.",
            }
        ]
    }


storage_server = create_sdk_mcp_server(
    name="storage",
    tools=[
        get_recent_events_tool,
        list_baselines_tool,
        log_event_tool,
        queue_decision_request_tool,
        escalate_immediately_tool,
    ],
)

ALLOWED_TOOLS = [
    "mcp__storage__get_recent_events",
    "mcp__storage__list_baselines",
    "mcp__storage__log_event",
    "mcp__storage__queue_decision_request",
    "mcp__storage__escalate_immediately",
]

PROMPT = """You are the Orchestrator for a multi-agent electric aircraft engineering project.
Your standing hard rule, checked against everything you do: safety issues, regulatory
issues, and irreversible-cost issues ALWAYS surface immediately via escalate_immediately —
never queued, never batched, no exceptions, regardless of how minor they might seem.
Everything else (real decision forks, routine progress) goes through the batching tools
(queue_decision_request / queue_digest_item / digest text) instead.

Do the following three tasks, in order:

TASK 1 — Directive decomposition
Directive from Saiyam: "Research whether a lighter battery placement could improve flight
endurance."
Decompose this into 2-3 concrete, specific open design questions that the Knowledge Base
and Innovation divisions would actually need to answer (not vague restatements of the
directive itself). Log this decomposition via log_event (event_type="directive_decomposition").
Then decide: does acting on this directive involve a real fork Saiyam should decide on right
now (e.g., whether to prioritize this over other open research threads)? If yes, call
queue_decision_request with a concrete question and 2-3 real options. This is a BATCHED
request — it does not go out immediately, it waits for the next batch.

TASK 2 — Escalation rule test
An incoming message arrives: "structural analysis shows a wing spar failure risk."
Classify it against the standing hard rule. If it qualifies (safety/regulatory/
irreversible-cost), call escalate_immediately with the correct category and a concrete
description — do NOT queue this as a decision request or digest item, and do not batch it.
Then explicitly explain, in your own words, exactly what property of this message makes it
escalate immediately instead of being handled like Task 1's decision request — be specific
about the distinguishing test you applied, not just "it sounds serious."

TASK 3 — Real milestone digest
Call get_recent_events (limit=20) and list_baselines to see REAL project history already in
the system (do not invent any of this — use exactly what comes back). Compile an actual
milestone digest: a short, real status summary of what's actually happened so far in this
project (agent runs, KB reconciliation, baselines created, etc.), written the way you'd
actually send it to Saiyam as a periodic update. This is example #2 of a batched
communication type, distinct from the decision request in Task 1.

Finally, output your results clearly labeled with these exact headers so they're easy to
tell apart:
## DIRECTIVE DECOMPOSITION
## DECISION REQUEST (batched example)
## ESCALATION (immediate example)
## MILESTONE DIGEST (batched example, built from real data)
## HOW ESCALATION DIFFERS FROM BATCHING (your reasoning)
"""


async def main():
    options = agent_runtime.build_options(
        system_prompt=(
            "You are the Orchestrator from a multi-agent electric aircraft engineering "
            "project. You enforce the escalation rule against everything you do, with no "
            "exceptions. Be precise and concrete — no filler, no vague restatements."
        ),
        storage_server=storage_server,
        allowed_tools=ALLOWED_TOOLS,
        max_turns=25,
    )

    stats = await agent_runtime.run_agent("Orchestrator", options, PROMPT)
    print(f"\n===== DONE — cost ${stats['cost']:.4f} =====")


if __name__ == "__main__":
    anyio.run(main)
