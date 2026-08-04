"""Safety & Risk — Wave 4, Assurance Gate division (CLAUDE.md).

Per CLAUDE.md: "FMEA and hazard analysis, including autonomy-specific
failure modes (lost GPS/navigation signal, sensor failure, loss of
comms/telemetry link) and cybersecurity/link security (GPS spoofing,
telemetry jamming). Escalates straight to Saiyam regardless of autonomy
tier. FMEA policy: delta-only re-run for minor baselines, full re-run
whenever structure, propulsion, or battery changes."

One of three genuinely separate, independent Assurance Gate offices. This
file deliberately does NOT import or reuse Regulatory's or Review & Critic's
tool implementations, even where the shape looks similar (get_baseline,
log_event) — every tool here is its own function object, and the
escalation path is its own independent implementation of the standing
project-wide escalation rule, not a call into Orchestrator's
escalate_immediately. Two offices independently reaching the same
conclusion through separately-written logic is a real cross-check; one
calling the other's code to save effort is not — it would be exactly the
"not merged, not one checking the other's box" failure CLAUDE.md warns
against.

REAL DATA THIS IS TESTED AGAINST RIGHT NOW: Software Engineer's real,
already-proposed failsafe stack (event 152-153-154: GPS-loss cruise
dead-reckon at a calculate()-derived best-glide speed, IMU-loss controlled
descent, telemetry-loss continue-mission, and the EMI mitigation plan for
requirement #31) is real, concrete, and available to hazard-analyze right
now. Per an Orchestrator directive run for real on 2026-07-31, full FMEA
was independently assessed as BLOCKED — CLAUDE.md's own policy requires a
full FMEA re-run whenever structure, propulsion, or battery changes, and
all three will change once VTOL architecture is selected (the span
re-derivation itself is done — baseline 210, 2026-08-02 — but that alone
doesn't unblock full FMEA; architecture selection still will), so running
full FMEA now would be immediately stale. The GPS-spoofing / telemetry-
jamming cybersecurity half of this
role, however, is architecture- and span-agnostic — it's about whether the
PROPOSED failsafe logic can be fooled, not about airframe geometry — so
this run is scoped to that slice only.

WHAT IT WILL NEED ONCE AVAILABLE: a converged baseline (post re-derivation)
and selected VTOL architecture, at which point a real, non-throwaway full
FMEA becomes possible and required by CLAUDE.md's own policy.
"""

import argparse
import json

import anyio
from claude_agent_sdk import create_sdk_mcp_server, tool

import agent_runtime
import agent_tools
import storage

AGENT_NAME = "SafetyRisk"

VALID_MITIGATION_STATES = {"MITIGATED", "PARTIALLY_MITIGATED", "UNMITIGATED"}
ESCALATION_CATEGORIES = {"safety", "regulatory", "irreversible_cost"}


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
    "record_hazard_finding",
    "Record ONE hazard finding against a specific real proposed mitigation. "
    "mitigation_status must be exactly MITIGATED, PARTIALLY_MITIGATED, or UNMITIGATED.",
    {
        "hazard": str,
        "target_proposal": str,
        "mitigation_status": str,
        "attack_or_failure_scenario": str,
        "recommendation": str,
    },
)
async def record_hazard_finding_tool(args):
    status = args["mitigation_status"].strip().upper()
    if status not in VALID_MITIGATION_STATES:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"[REJECTED] mitigation_status must be one of "
                    f"{sorted(VALID_MITIGATION_STATES)}, got {args['mitigation_status']!r}.",
                }
            ],
            "is_error": True,
        }
    if not args["attack_or_failure_scenario"].strip():
        return {
            "content": [
                {
                    "type": "text",
                    "text": "[REJECTED] attack_or_failure_scenario must describe a concrete real "
                    "scenario — a hazard finding with no scenario is not a hazard analysis.",
                }
            ],
            "is_error": True,
        }
    description = (
        f"HAZARD: {args['hazard']} | TARGET: {args['target_proposal']} | "
        f"STATUS: {status} | SCENARIO: {args['attack_or_failure_scenario']} | "
        f"RECOMMENDATION: {args['recommendation']}"
    )
    storage.log_event(AGENT_NAME, "hazard_finding", description)
    if status == "UNMITIGATED":
        storage.log_event(AGENT_NAME, "cluster_objection", description)
    return {"content": [{"type": "text", "text": f"Recorded {status} for hazard: {args['hazard'][:70]}"}]}


@tool(
    "escalate_hazard",
    "Escalate a real safety hazard to Saiyam RIGHT NOW, bypassing all batching — "
    "per CLAUDE.md's standing rule that Safety & Risk escalates straight to Saiyam "
    "regardless of autonomy tier. category must be exactly 'safety'.",
    {"category": str, "description": str},
)
async def escalate_hazard_tool(args):
    category = args["category"]
    if category not in ESCALATION_CATEGORIES:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"[REJECTED] category must be one of {sorted(ESCALATION_CATEGORIES)}, "
                    f"got {category!r}.",
                }
            ],
            "is_error": True,
        }
    storage.log_event(AGENT_NAME, "escalation", f"[{category.upper()}] {args['description']}")
    return {
        "content": [
            {"type": "text", "text": f"ESCALATED IMMEDIATELY (category={category})."}
        ]
    }


log_event_tool = agent_tools.make_log_event_tool(AGENT_NAME)

ALLOWED_TOOLS = [
    "mcp__storage__search_kb",
    "mcp__storage__get_recent_events",
    "mcp__storage__list_requirements",
    "mcp__storage__record_hazard_finding",
    "mcp__storage__escalate_hazard",
    "mcp__storage__log_event",
]

storage_server = create_sdk_mcp_server(
    name="storage",
    tools=[
        agent_tools.search_kb_tool,
        get_recent_events_tool,
        list_requirements_tool,
        record_hazard_finding_tool,
        escalate_hazard_tool,
        log_event_tool,
    ],
)

PROMPT = """You are the Safety & Risk office of the Assurance Gate for a
multi-agent electric aircraft project — one of three genuinely separate,
independent offices (the other two are Review & Critic and Regulatory). You
do not coordinate your verdict with them, and you do not defer to whether
they found a problem.

SCOPE FOR THIS RUN — CYBERSECURITY / LINK SECURITY ONLY:
Full FMEA is explicitly OUT OF SCOPE right now. CLAUDE.md's own FMEA policy
requires a full re-run whenever structure, propulsion, or battery changes —
VTOL architecture is still unselected, which WILL change those systems once
it's picked (the span re-derivation itself is already done — baseline 210 —
but that alone doesn't unblock full FMEA). Running full FMEA now would be
immediately stale. Instead, hazard-analyze the cybersecurity/
link-security half of your role (GPS spoofing, telemetry jamming), which is
architecture- and span-agnostic, against Software Engineer's real, already-
proposed failsafe logic.

Steps:
1. get_recent_events filtered to event_type="software_proposal" (and
   "cluster_objection") with a generous limit to read Software Engineer's
   real proposed failsafe logic in full: GPS-loss cruise dead-reckon
   behavior, IMU-loss controlled descent, telemetry-loss continue-mission,
   and the EMI mitigation plan for requirement #31. Read the actual
   proposal text, not a summary.
2. list_requirements(baseline_id=0) and read requirement #30 (failsafe
   timing/testability) and requirement #31 (EMI/EMC) in full.
3. Hazard-analyze at least these real attack/failure scenarios against the
   REAL proposed logic (not a generic autopilot — this specific proposal):
   (a) GPS SPOOFING: Software Engineer's GPS-loss failsafe triggers on EKF
       innovation-gate exceedance or low satellite count/HDOP — but a
       competent spoofing attack feeds a smoothly consistent FALSE position
       that may not trip an innovation gate at all. Does the proposed logic
       have any defense against a CONSISTENT false GPS signal, or only
       against GPS being absent/noisy? (b) TELEMETRY JAMMING: the proposed
       behavior for telemetry loss is "continue the pre-loaded mission
       autonomously." Is that actually a safe response to jamming
       specifically (vs. benign range loss), or could an attacker use
       jamming timed to a specific mission phase to exploit that exact
       behavior? (c) Any other real scenario the proposal's own text
       exposes once you read it closely.
4. For each, record_hazard_finding with a real mitigation_status. Use
   MITIGATED only where the proposal's actual text already handles the
   scenario — quote it. Use UNMITIGATED or PARTIALLY_MITIGATED honestly
   where it doesn't; do not round up.
5. If you find a genuine UNMITIGATED hazard with real safety consequence
   (not merely undesirable — genuinely a risk to the aircraft or people
   near it), call escalate_hazard immediately per CLAUDE.md's standing
   rule that Safety & Risk escalates straight to Saiyam regardless of
   autonomy tier. Do not escalate a merely partially-mitigated or
   low-consequence finding — that would devalue the rule for the finding
   that actually needs it.
6. Finish with ONE log_event, event_type="safety_risk_review_complete",
   summarizing every finding and stating plainly that full FMEA is
   deferred until baseline re-derivation and VTOL architecture selection,
   per CLAUDE.md's own re-run policy.
"""


async def main():
    parser = argparse.ArgumentParser(
        description="Safety & Risk — cybersecurity/link-security hazard analysis (Assurance Gate)"
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
