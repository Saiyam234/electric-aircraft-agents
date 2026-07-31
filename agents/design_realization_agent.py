"""Design Realization Agent — Wave 3, Concurrent Engineering Cluster (CLAUDE.md).

Per CLAUDE.md: "writes Fusion 360 Python API scripts once the cluster's spec
is locked to a baseline (manual script handoff, above)." The handoff is
manual by design (see CLAUDE.md's "Tech stack" section): Saiyam opens
Fusion 360 and runs the generated script himself.

REAL DATA THIS IS TESTED AGAINST RIGHT NOW: baseline 89's real, already-
computed wing planform (span, area, root/tip chord, MAC, taper ratio) and
Airframe Engineer's real airfoil selection (SD7003, event 92). That is
genuinely enough to generate a real wing-planform sketch/loft script.

WHAT IT WILL NEED ONCE AVAILABLE — read this before trusting the output:
1. Baseline 89's own wingspan (1.25 m) is STALE. Saiyam decided 2026-07-29
   (D1 event 117) that the 1:8 basis is an absolute 1.40 m target, not a
   ratio — but baseline 89 has never been re-derived against that decision
   (flagged in CLAUDE.md's "Still open" section). This agent does NOT
   silently rescale baseline 89's numbers itself — that would be exactly the
   kind of unrequested inline engineering judgment CLAUDE.md's rules exist
   to prevent, and Design Realization Agent's job is to realize a LOCKED
   spec, not to re-derive one. It generates the wing at baseline 89's
   current stored dimensions and prints/logs a prominent, impossible-to-miss
   flag that the script must be regenerated once baseline 89 is corrected.
2. VTOL architecture is not selected, so there is no fuselage, tail, or
   lift-system geometry to realize yet — only the wing planform is
   architecture-agnostic enough to generate today. This run is scoped to the
   wing only, not the aircraft.
3. Real R2 storage exists in this project but is not unlocked (needs a card
   on file) — irrelevant here anyway, since CLAUDE.md's own workflow for
   this handoff is local file + manual Fusion 360 run, not cloud storage.
   The generated script is written to fusion_scripts/ in this repo.
"""

import argparse
import json
import os
import re

import anyio
from claude_agent_sdk import create_sdk_mcp_server, tool

import agent_runtime
import agent_tools
import storage

AGENT_NAME = "DesignRealizationAgent"

OUTPUT_DIR = "fusion_scripts"
_SAFE_FILENAME = re.compile(r"^[a-zA-Z0-9_\-]+\.py$")


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
    rows = storage.get_audit_log(limit=int(args.get("limit", 30) or 30))
    event_type = (args.get("event_type") or "").strip()
    if event_type:
        rows = [r for r in rows if r["event_type"] == event_type]
    return {"content": [{"type": "text", "text": json.dumps(rows, default=str)}]}


@tool(
    "save_fusion_script",
    "Save a real Fusion 360 Python API script to disk for manual handoff. filename "
    "must be a plain name ending in .py (no path separators). script_content is the "
    "full real Python source, not a placeholder.",
    {"filename": str, "script_content": str, "scope_note": str},
)
async def save_fusion_script_tool(args):
    filename = args["filename"].strip()
    if not _SAFE_FILENAME.match(filename):
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"[REJECTED] filename must match {_SAFE_FILENAME.pattern} — "
                    f"got {filename!r}. No path separators or extensions other than .py.",
                }
            ],
            "is_error": True,
        }
    content = args["script_content"]
    if "import adsk" not in content:
        return {
            "content": [
                {
                    "type": "text",
                    "text": "[REJECTED] script_content does not import the Fusion 360 'adsk' API — "
                    "this does not look like a real Fusion 360 Python API script.",
                }
            ],
            "is_error": True,
        }

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w") as f:
        f.write(content)

    storage.log_event(
        AGENT_NAME,
        "fusion_script_saved",
        f"FILE: {path} | SCOPE: {args['scope_note']}",
    )
    return {
        "content": [
            {
                "type": "text",
                "text": f"Saved {len(content)} bytes to {path}. Manual handoff: Saiyam opens "
                "Fusion 360 and runs this script himself (per CLAUDE.md's tech stack section).",
            }
        ]
    }


log_event_tool = agent_tools.make_log_event_tool(AGENT_NAME)

ALLOWED_TOOLS = [
    "mcp__storage__search_kb",
    "mcp__storage__list_baselines",
    "mcp__storage__get_baseline",
    "mcp__storage__get_recent_events",
    "mcp__storage__save_fusion_script",
    "mcp__storage__log_event",
]

storage_server = create_sdk_mcp_server(
    name="storage",
    tools=[
        agent_tools.search_kb_tool,
        list_baselines_tool,
        get_baseline_tool,
        get_recent_events_tool,
        save_fusion_script_tool,
        log_event_tool,
    ],
)

PROMPT = """You are the Design Realization Agent for a multi-agent electric
aircraft project. Your job is narrow and mechanical: translate an ALREADY-
LOCKED numeric spec into a real Fusion 360 Python API script. You do not
decide dimensions, pick materials, or re-derive anything — you realize
numbers that other agents already computed and stored.

You do not have a calculate tool. If you find yourself wanting to compute a
new number rather than read one directly from a stored baseline or a prior
agent's real review, stop — that number belongs to Math & Physics Engine or
Airframe Engineer, not you. Read it from get_baseline or get_recent_events
instead.

CRITICAL — SCOPE IS THE WING ONLY, AND THE SPAN IS KNOWN STALE:
1. get_baseline(89) and read its real "dimensions" section (wingspan, wing
   area, root chord, tip chord, MAC, taper ratio) — these came from a
   PLACEHOLDER reference that was never re-derived against the wingspan
   Saiyam actually decided (1.40 m absolute, D1 event 117, 2026-07-29).
   Use baseline 89's stored numbers exactly as they are — do NOT rescale
   them yourself, that is not your job and not how this project verifies
   numbers. Instead, put an unmissable comment block at the very top of the
   generated script stating the real span it was generated from, the real
   decided target it does NOT yet reflect, and that it must be regenerated
   once baseline 89 is corrected.
2. get_recent_events filtered to event_type="airframe_review_complete" to
   read Airframe Engineer's real airfoil decision (SD7003) for a comment
   noting which airfoil profile a real geometry pass would loft between —
   you are not expected to embed real SD7003 coordinate data yourself in
   this pass; note in the script and in your final log_event that true
   airfoil-profile lofting needs real SD7003 coordinate data as a follow-up.
3. VTOL architecture is not selected, so do not attempt fuselage, tail, or
   lift-system geometry. Wing planform only.
4. Write a real, runnable Fusion 360 Python API script: a real `def run(context):`
   entry point using `import adsk.core, adsk.fusion, adsk.cam`, that creates
   a sketch on the XZ plane, draws the real trapezoidal planform (root chord
   at the centerline, tip chord at the real semi-span, straight leading edge
   for now since sweep isn't specified anywhere real), and extrudes/mirrors
   it. It should be something Saiyam could actually attempt to run, not
   pseudocode.
5. Call save_fusion_script with filename="wing_planform.py", the real script
   content, and a scope_note stating plainly: real numbers used, from which
   baseline, and the known-stale-span caveat.
6. Finish with ONE log_event, event_type="design_realization_complete",
   stating what was generated, what real data it came from, and what remains
   blocked (baseline re-derivation, VTOL architecture, real airfoil
   coordinates) before a full-aircraft script is possible.
"""


async def main():
    argparse.ArgumentParser(
        description="Design Realization Agent — wing-only Fusion 360 script from baseline 89"
    ).parse_args()

    options = agent_runtime.build_options(
        system_prompt=PROMPT,
        storage_server=storage_server,
        allowed_tools=ALLOWED_TOOLS,
        max_turns=40,
    )
    stats = await agent_runtime.run_agent(AGENT_NAME, options, PROMPT)
    print(f"\n===== DONE — cost ${stats['cost']:.4f} =====")


if __name__ == "__main__":
    anyio.run(main)
