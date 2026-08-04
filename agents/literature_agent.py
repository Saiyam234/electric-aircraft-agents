"""Literature Agent — Literature division (CLAUDE.md).

Per CLAUDE.md: "drafts the interim document at every baseline and the
capstone paper at project completion, handles citation/formatting, and
self-reviews before feeding the result back into the Knowledge Base."

REAL DATA THIS IS TESTED AGAINST: CLAUDE.md's "interim document" is
specifically tied to a real milestone — a baseline that has cleared the
Assurance Gate (all three offices signed off, storage.is_baseline_stamped()
true). No baseline has ever been stamped. Writing something and CALLING it
"the interim document" would misrepresent a milestone that hasn't happened —
exactly the kind of fabrication this project's rules exist to prevent. So
this agent structurally checks is_baseline_stamped() itself (Python, not the
model's word) before it will let a document be saved as doc_type
"interim_document"; right now that check will fail, and the real, honest
product is a dated STATUS MEMO instead — a real, citable snapshot of actual
verified project state, explicitly labeled as not the CLAUDE.md milestone
deliverable.

Never fetches a hardcoded baseline id — see CLAUDE.md's Wave 4 review-pass
note (2026-08-02) on why that was a real bug in six other agents.
"""

from __future__ import annotations

import argparse
import json
import os
import re

import anyio
from claude_agent_sdk import create_sdk_mcp_server, tool

import agent_runtime
import agent_tools
import storage

AGENT_NAME = "LiteratureAgent"

MAX_TURNS = 45
TURN_WARNING_THRESHOLD = int(MAX_TURNS * 0.8)

OUTPUT_DIR = "literature"
_SAFE_FILENAME = re.compile(r"^[a-zA-Z0-9_\-]+\.md$")
MIN_CONTENT_CHARS = 1500
VALID_DOC_TYPES = {"status_memo", "interim_document"}


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
    "check_baseline_stamped",
    "Real check (not your judgment) of whether a baseline has actually cleared "
    "the Assurance Gate (all three offices signed off).",
    {"baseline_id": float},
)
async def check_baseline_stamped_tool(args):
    stamped = storage.is_baseline_stamped(int(args["baseline_id"]))
    return {"content": [{"type": "text", "text": json.dumps({"baseline_id": int(args["baseline_id"]), "stamped": stamped})}]}


@tool(
    "get_recent_events",
    "Read the N most recent audit-log events, optionally filtered by event_type "
    "(empty string = all types)",
    {"limit": float, "event_type": str},
)
async def get_recent_events_tool(args):
    event_type = (args.get("event_type") or "").strip() or None
    rows = storage.get_audit_log(limit=int(args.get("limit", 80) or 80), event_type=event_type)
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
    "save_document",
    "Save a real Markdown document to disk. doc_type must be exactly 'status_memo' "
    "or 'interim_document' — 'interim_document' is REJECTED unless the named "
    "baseline_id is actually stamped (checked here, not taken on your word). "
    "filename must be a plain name ending in .md. content_markdown is the full "
    "real document, not a placeholder or outline.",
    {"filename": str, "doc_type": str, "baseline_id": float, "content_markdown": str},
)
async def save_document_tool(args):
    doc_type = args["doc_type"].strip().lower()
    if doc_type not in VALID_DOC_TYPES:
        return {
            "content": [{"type": "text", "text": f"[REJECTED] doc_type must be one of {sorted(VALID_DOC_TYPES)}."}],
            "is_error": True,
        }
    if doc_type == "interim_document":
        baseline_id = int(args["baseline_id"])
        if not baseline_id or not storage.is_baseline_stamped(baseline_id):
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"[REJECTED] baseline {baseline_id or '(none given)'} is not stamped "
                        "(all three Assurance offices have not signed off) — this cannot be saved as "
                        "doc_type='interim_document'. Save it as doc_type='status_memo' instead; that "
                        "is the honest current milestone.",
                    }
                ],
                "is_error": True,
            }

    filename = args["filename"].strip()
    if not _SAFE_FILENAME.match(filename):
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"[REJECTED] filename must match {_SAFE_FILENAME.pattern} — got {filename!r}. "
                    "No path separators or extensions other than .md.",
                }
            ],
            "is_error": True,
        }

    content = args["content_markdown"]
    if len(content) < MIN_CONTENT_CHARS:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"[REJECTED] content_markdown is only {len(content)} chars (minimum "
                    f"{MIN_CONTENT_CHARS}) — this looks like an outline, not a real document.",
                }
            ],
            "is_error": True,
        }
    if "http" not in content:
        return {
            "content": [
                {
                    "type": "text",
                    "text": "[REJECTED] no citation URLs found in the document — a status document "
                    "with real findings should cite real Knowledge Base sources.",
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
        "document_saved",
        f"FILE: {path} | DOC_TYPE: {doc_type} | CHARS: {len(content)}",
    )
    return {"content": [{"type": "text", "text": f"Saved {len(content)} chars to {path} as doc_type={doc_type}."}]}


log_event_tool = agent_tools.make_log_event_tool(AGENT_NAME)

ALLOWED_TOOLS = [
    "mcp__storage__search_kb",
    "mcp__storage__list_baselines",
    "mcp__storage__get_baseline",
    "mcp__storage__check_baseline_stamped",
    "mcp__storage__get_recent_events",
    "mcp__storage__list_requirements",
    "mcp__storage__save_document",
    "mcp__storage__log_event",
]

storage_server = create_sdk_mcp_server(
    name="storage",
    tools=[
        agent_tools.search_kb_tool,
        list_baselines_tool,
        get_baseline_tool,
        check_baseline_stamped_tool,
        get_recent_events_tool,
        list_requirements_tool,
        save_document_tool,
        log_event_tool,
    ],
)

PROMPT = f"""You are the Literature Agent for a multi-agent electric aircraft
project. CLAUDE.md's role for you is drafting "the interim document at every
baseline" — but that is specifically tied to a baseline that has cleared the
Assurance Gate, and none has. Calling something "the interim document" when
no baseline is actually stamped would misrepresent a milestone that hasn't
happened. Your real job THIS RUN is the honest version of that: a real,
dated STATUS MEMO — a genuine snapshot of actual verified project state,
citing real sources — explicitly labeled as a working document, not the
CLAUDE.md milestone deliverable.

TURN BUDGET: you have a hard limit of {MAX_TURNS} conversation turns for this
ENTIRE task. If you are past turn {TURN_WARNING_THRESHOLD} and not done, stop
researching and write with whatever real material you have — a shorter, real
memo beats an incomplete run.

ABSOLUTE RULE — NEVER FABRICATE A FINDING OR CITATION:
Every technical claim in the document must trace to something you actually
read this run — a real baseline field, a real logged event, a real KB
search result with a real source URL. Do not restate a number from memory of
earlier conversation; look it up again this run so what you write is
grounded in what you actually verified now.

Steps:
1. Call list_baselines, then get_baseline on the most recent one whose
   version starts "v0.1-config-draft" — never a hardcoded id.
2. Call check_baseline_stamped on that baseline's real id. Note the real
   result plainly in the document — do not assume either way.
3. get_recent_events with a generous limit (80+) and no type filter to read
   the real, actual project history — what's been decided, what's been
   proven, what's been escalated, what remains open. Read the real text.
4. list_requirements(baseline_id=0) for the real, current set of approved
   requirements.
5. search_kb for the real citations backing the technical claims you plan to
   make — pull real source titles/URLs, do not paraphrase from memory.
6. Write a real Markdown status memo covering, with real citations
   throughout: (a) current configuration state and its real key numbers,
   (b) what's been decided vs. still open (hard constraints, VTOL
   architecture), (c) real findings worth recording (e.g. real bugs found
   and fixed, real safety escalations, real cross-checks), (d) what remains
   before a baseline can actually be stamped. This is a real document
   someone could read to understand actual current state — not a table of
   contents or a summary of a summary.
7. Call save_document with doc_type="status_memo" (interim_document will be
   rejected unless the baseline is actually stamped, which step 2 will have
   already told you). Use a real, dated filename like
   "status-memo-2026-08-02.md".
8. Finish with ONE log_event, event_type="literature_complete", summarizing
   what was written and stating plainly that this is a status memo, not the
   CLAUDE.md-defined interim document, because no baseline is stamped yet.
"""


async def main():
    parser = argparse.ArgumentParser(
        description="Literature Agent — real dated status memo (not the CLAUDE.md interim document; no baseline is stamped yet)"
    )
    parser.add_argument("--message", help="A real message from Saiyam for this run (direct chat).")
    args = parser.parse_args()

    options = agent_runtime.build_options(
        system_prompt=(
            "You are the Literature Agent from a multi-agent electric aircraft "
            "engineering project. Every claim in your document must trace to something "
            "real you read this run — never fabricate a finding, number, or citation."
        ),
        storage_server=storage_server,
        allowed_tools=ALLOWED_TOOLS,
        max_turns=MAX_TURNS,
    )
    stats = await agent_runtime.run_agent(AGENT_NAME, options, PROMPT, steer_message=args.message)
    print(f"\n===== DONE — cost ${stats['cost']:.4f} =====")


if __name__ == "__main__":
    anyio.run(main)
