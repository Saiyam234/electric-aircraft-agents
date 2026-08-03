"""Manufacturing Manager — Manufacturing division (CLAUDE.md).

Per CLAUDE.md: "compiles the bill of materials, researches sourcing/
vendors, drafts the build sequence, tracks running cost. Produces drafts
only — no purchase or build commitment until full Assurance sign-off and
Saiyam's explicit approval. Explicitly flags manufacturability problems
back to the Engineering Cluster when something is impractical to
fabricate."

REAL DATA THIS IS TESTED AGAINST: a real, honest tension — a full BOM is
NOT possible yet, because VTOL architecture (tiltrotor/tiltwing/lift+cruise/
tailsitter) is still unselected, and that decision drives motor count,
mount hardware, and a meaningful share of the airframe. Rather than either
refusing to run or fabricating a full-aircraft BOM against a design that
doesn't exist, this agent is scoped like Safety & Risk's Wave 4 run was
(cybersecurity-only, not full FMEA): cost real, architecture-AGNOSTIC
components only — the wing structure (from the current baseline's real
dimensions + KB composite-layup evidence) and the battery pack (a fixed
input regardless of VTOL architecture) — and explicitly, loudly flag every
architecture-dependent component (motors, ESCs, mounts, tilt mechanism,
fuselage) as NOT costed, blocked pending architecture selection, rather
than silently omitting them or guessing.

Never fetches a hardcoded baseline id — every agent in this project that
did that had to be fixed once baseline 210 superseded baseline 89 (see
CLAUDE.md's Wave 4 review-pass note, 2026-08-02). Always fetches whichever
baseline is actually most recent.
"""

from __future__ import annotations

import argparse
import json

import anyio
from claude_agent_sdk import create_sdk_mcp_server, tool

import agent_runtime
import agent_tools
import storage

AGENT_NAME = "ManufacturingManager"

MAX_TURNS = 45
TURN_WARNING_THRESHOLD = int(MAX_TURNS * 0.8)

_bom_items: list[dict] = []


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
    "record_bom_item",
    "Record ONE real, sourceable BOM line item. quantity and unit_cost_usd are "
    "numbers; this tool computes the line total itself — never state a line total "
    "in your own reasoning text. architecture_dependent must be exactly 'true' or "
    "'false'. If true, unit_cost_usd/vendor/source_url may be 'unknown' (blocked, "
    "not costed) — but part_name and rationale must still explain why it's blocked.",
    {
        "part_name": str,
        "category": str,
        "quantity": float,
        "unit_cost_usd": float,
        "vendor": str,
        "source_url": str,
        "architecture_dependent": str,
        "rationale": str,
    },
)
async def record_bom_item_tool(args):
    dependent = args["architecture_dependent"].strip().lower()
    if dependent not in ("true", "false"):
        return {
            "content": [
                {"type": "text", "text": "[REJECTED] architecture_dependent must be exactly 'true' or 'false'."}
            ],
            "is_error": True,
        }
    is_dependent = dependent == "true"
    quantity = args["quantity"]
    unit_cost = args["unit_cost_usd"]
    if not is_dependent:
        if quantity <= 0:
            return {
                "content": [{"type": "text", "text": "[REJECTED] quantity must be > 0 for a real, costed item."}],
                "is_error": True,
            }
        if unit_cost < 0:
            return {
                "content": [{"type": "text", "text": "[REJECTED] unit_cost_usd cannot be negative."}],
                "is_error": True,
            }
        if not args["source_url"].strip() or args["source_url"].strip().lower() == "unknown":
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "[REJECTED] a costed, non-architecture-dependent item needs a real "
                        "source_url — an uncited price is exactly the kind of fabricated number this "
                        "project's rules exist to prevent. Use WebSearch to find one, or mark this "
                        "item architecture_dependent=true if it genuinely can't be sourced yet.",
                    }
                ],
                "is_error": True,
            }
    line_total = round(quantity * unit_cost, 2) if not is_dependent else None
    item = {
        "part_name": args["part_name"],
        "category": args["category"],
        "quantity": quantity,
        "unit_cost_usd": unit_cost if not is_dependent else None,
        "line_total_usd": line_total,
        "vendor": args["vendor"],
        "source_url": args["source_url"],
        "architecture_dependent": is_dependent,
        "rationale": args["rationale"],
    }
    _bom_items.append(item)
    return {
        "content": [
            {
                "type": "text",
                "text": f"Recorded BOM item #{len(_bom_items)}: {args['part_name']}"
                + (f" — line total ${line_total:.2f}" if line_total is not None else " — BLOCKED, not costed"),
            }
        ]
    }


@tool(
    "finalize_bom",
    "Finalize the BOM: computes the real running total itself from every recorded "
    "item (never state a grand total in your own reasoning text), logs it, and "
    "closes out the run. Call this exactly once, after all real items are recorded.",
    {"build_sequence_notes": str, "manufacturability_flags": str},
)
async def finalize_bom_tool(args):
    if not _bom_items:
        return {
            "content": [{"type": "text", "text": "[REJECTED] no BOM items recorded — nothing to finalize."}],
            "is_error": True,
        }
    costed = [i for i in _bom_items if not i["architecture_dependent"]]
    blocked = [i for i in _bom_items if i["architecture_dependent"]]
    total = round(sum(i["line_total_usd"] for i in costed), 2)
    description = (
        f"COSTED_ITEMS: {len(costed)} | BLOCKED_ITEMS: {len(blocked)} | "
        f"REAL_RUNNING_TOTAL_USD: {total} | "
        f"BLOCKED_PARTS: {', '.join(i['part_name'] for i in blocked) or 'none'} | "
        f"BUILD_SEQUENCE: {args['build_sequence_notes']} | "
        f"MANUFACTURABILITY_FLAGS: {args['manufacturability_flags']} | "
        f"FULL_BOM_JSON: {json.dumps(_bom_items, default=str)}"
    )
    storage.log_event(AGENT_NAME, "bom_drafted", description)
    return {
        "content": [
            {
                "type": "text",
                "text": f"Finalized draft BOM: {len(costed)} real costed items totaling ${total:.2f}, "
                f"{len(blocked)} blocked pending architecture selection. Draft only — no purchase "
                "or build commitment per CLAUDE.md; requires full Assurance sign-off and Saiyam's "
                "explicit approval before any real spend.",
            }
        ]
    }


log_event_tool = agent_tools.make_log_event_tool(AGENT_NAME)

ALLOWED_TOOLS = [
    "WebSearch",
    "mcp__storage__search_kb",
    "mcp__storage__list_baselines",
    "mcp__storage__get_baseline",
    "mcp__storage__list_requirements",
    "mcp__storage__record_bom_item",
    "mcp__storage__finalize_bom",
    "mcp__storage__log_event",
]

storage_server = create_sdk_mcp_server(
    name="storage",
    tools=[
        agent_tools.search_kb_tool,
        list_baselines_tool,
        get_baseline_tool,
        list_requirements_tool,
        record_bom_item_tool,
        finalize_bom_tool,
        log_event_tool,
    ],
)

PROMPT = f"""You are the Manufacturing Manager for a multi-agent electric aircraft
project. Your real job right now: draft a real, partial bill of materials —
architecture-agnostic components only — and explicitly, loudly flag every
component that depends on the still-unselected VTOL architecture as blocked,
rather than costing a full aircraft that doesn't exist yet or silently
skipping the parts you can't source.

TURN BUDGET: you have a hard limit of {MAX_TURNS} conversation turns for this
ENTIRE task. If you are past turn {TURN_WARNING_THRESHOLD} and not done, stop
researching and finalize with whatever real items you have — a smaller, real
BOM beats an incomplete run.

ABSOLUTE RULE — NEVER DO ARITHMETIC YOURSELF:
record_bom_item computes each line total; finalize_bom computes the real
grand total. Never state a line total or grand total in your own reasoning
text before calling these tools — if your mental math and the tool's real
computed number would ever disagree, the tool's number is correct.

ABSOLUTE RULE — NEVER FABRICATE A PRICE OR VENDOR:
Every costed (non-architecture-dependent) item needs a real, current source —
use WebSearch to find a real vendor and price. record_bom_item rejects a
costed item with no real source_url. If you cannot find a real current price
for something that should be sourceable, mark it architecture_dependent=true
with a rationale explaining what's actually missing — do not invent a
plausible-sounding number.

Steps:
1. Call list_baselines, then get_baseline on the most recent one whose
   version starts "v0.1-config-draft" — never a hardcoded baseline id, since
   the current baseline changes as the cluster re-derives it. Read its real
   wing dimensions (span, area, root/tip chord) and real battery pack spec
   (cell count, capacity, mass budget) — both of these are architecture-
   agnostic, fixed regardless of which VTOL mechanism is eventually chosen.
2. search_kb for real composite-layup and structural-material evidence (spar
   caps, skin layup, core material) to ground real wing-structure BOM items —
   pull real figures rather than assuming standard hobby-RC materials.
3. list_requirements(baseline_id=0) and check for any real requirement that
   constrains materials or handling (e.g. the LiPo battery-handling
   requirements) — a BOM that ignores an approved requirement is a real gap.
4. Use WebSearch to find real, current vendors and prices for the
   architecture-agnostic items: wing spar material (CFRP/T300 UD tow or
   pultruded cap stock), wing skin/core material, the battery pack (a real
   4S LiPo pack matching the baseline's real capacity), and basic build
   consumables (epoxy/adhesive, fasteners) if a real requirement or KB
   source names something specific. Call record_bom_item for each real,
   sourced item.
5. For every component that genuinely depends on the unselected VTOL
   architecture — motors, ESCs, propellers/rotors, motor mounts, tilt
   mechanism hardware, fuselage structure — call record_bom_item with
   architecture_dependent="true" and a rationale naming exactly what
   architecture decision would unblock it. Do not guess a plausible
   configuration to avoid leaving it blocked.
6. If you notice a real manufacturability concern (e.g. a material or
   process that would be genuinely impractical for a solo build at this
   scale), note it — this is explicitly part of the role per CLAUDE.md
   ("flags manufacturability problems back to the Engineering Cluster").
   If you find none, say so plainly rather than inventing one.
7. Call finalize_bom exactly once with real build-sequence notes (a rough,
   honest order of operations for what CAN be built now — the wing
   structure — not a full-aircraft assembly sequence that doesn't exist
   yet) and any manufacturability flags from step 6.
8. Finish with ONE log_event, event_type="manufacturing_manager_complete",
   summarizing the real costed total, what's blocked and why, and stating
   plainly that this is a draft only — CLAUDE.md requires full Assurance
   sign-off AND Saiyam's explicit approval before any real purchase or
   build commitment, which this run does not grant.
"""


async def main():
    argparse.ArgumentParser(
        description="Manufacturing Manager — real, partial BOM draft (architecture-agnostic components only)"
    ).parse_args()

    options = agent_runtime.build_options(
        system_prompt=(
            "You are the Manufacturing Manager from a multi-agent electric aircraft "
            "engineering project. Every cost you record must be a real, currently-sourced "
            "figure or explicitly marked blocked — never a fabricated or estimated price."
        ),
        storage_server=storage_server,
        allowed_tools=ALLOWED_TOOLS,
        builtin_tools=["WebSearch"],
        max_turns=MAX_TURNS,
    )
    stats = await agent_runtime.run_agent(AGENT_NAME, options, PROMPT)
    print(f"\n===== DONE — cost ${stats['cost']:.4f} =====")


if __name__ == "__main__":
    anyio.run(main)
