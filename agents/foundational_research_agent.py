"""Foundational Research Agent (Knowledge Base division, per CLAUDE.md).

Proactively builds the reference library using REAL web search — not
synthesis from the model's own training knowledge. Each distinct fact found
gets its own knowledge-base entry (via storage.upsert_kb_checked) tagged
with topic and source metadata, so it stays precise and individually
searchable later. One research event is logged via storage.log_event per
topic when done.

Exact duplicates (re-running the same topic and regenerating the same
descriptive entry_id) are rejected at write time by upsert_kb_checked and
logged as duplicate_detected events rather than silently overwritten —
see README.md's Deduplication strategy section. Near-duplicates under a
different entry_id aren't caught here; that's KB Manager's job.

Usage:
    python3 foundational_research_agent.py --topic "structural materials"
    python3 foundational_research_agent.py --topic "X" --topic "Y"   # multiple custom topics
    python3 foundational_research_agent.py --all                    # the 6 CLAUDE.md topics
    python3 foundational_research_agent.py --all --topic "extra one" # all 6 plus a custom one

Each topic runs in its own conversation, storing facts incrementally as it
finds them (not batched at the end) so a hard cutoff doesn't lose completed
work. If a topic's run genuinely errors out, it's retried once. If it
instead runs out of its turn budget on a broad topic, that's treated as an
expected "partial" outcome (not retried — retrying would just re-run the
same broad topic into the same ceiling again) and flagged for a narrower
follow-up topic rather than failing the batch.
"""

import argparse
import re
import sys

import anyio

import agent_runtime
import storage
from claude_agent_sdk import create_sdk_mcp_server, tool

MAX_TURNS = 60
TURN_WARNING_THRESHOLD = int(MAX_TURNS * 0.8)

# The six core topics named in CLAUDE.md for the initial foundational sweep.
CORE_TOPICS = [
    "aerodynamics fundamentals",
    "electric propulsion",
    "battery chemistry and safety",
    "prior electric aircraft designs",
    "structural materials",
    "autonomous flight systems",
]


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


@tool(
    "upsert_kb",
    "Store one specific, precise fact/finding in the knowledge base, with source metadata",
    {
        "entry_id": str,
        "text": str,
        "topic": str,
        "source_url": str,
        "source_title": str,
    },
)
async def upsert_kb_tool(args):
    try:
        storage.upsert_kb_checked(
            args["entry_id"],
            args["text"],
            metadata={
                "topic": args["topic"],
                "source_url": args["source_url"],
                "source_title": args["source_title"],
            },
        )
        return {"content": [{"type": "text", "text": f"Stored KB entry id={args['entry_id']}"}]}
    except ValueError as exc:
        # Duplicate entry_id — log it and tell the agent to move on rather than crash.
        storage.log_event("FoundationalResearchAgent", "duplicate_detected", f"entry_id={args['entry_id']}: {exc}")
        return {"content": [{"type": "text", "text": f"[SKIP] entry_id={args['entry_id']} already exists — duplicate rejected"}]}


@tool("log_event", "Log a research event to the audit log", {"event_type": str, "description": str})
async def log_event_tool(args):
    storage.log_event("FoundationalResearchAgent", args["event_type"], args["description"])
    return {"content": [{"type": "text", "text": "Logged event"}]}


storage_server = create_sdk_mcp_server(
    name="storage",
    tools=[upsert_kb_tool, log_event_tool],
)

ALLOWED_TOOLS = ["WebSearch", "mcp__storage__upsert_kb", "mcp__storage__log_event"]


def build_prompt(topic: str, topic_tag: str) -> str:
    return f"""You are the Foundational Research Agent for a multi-agent electric aircraft
engineering project. Research this ONE topic using REAL web search (do not rely on your
own training knowledge alone — actually search and pull from real sources):

TOPIC: "{topic}"

SCOPE — read this before you start searching:
Prioritize depth on the topic's core fundamentals over attempting exhaustive coverage.
Extract the most important, highest-value facts first — the things an engineer would need
before anything else. For a normal-sized topic, aim for roughly 15-25 solid entries; that
is a target for a well-scoped topic, not a hard cap and not a quota to pad out. Quality and
correctness matter more than hitting a number.

Some topics are genuinely broad and span many distinct sub-areas (e.g. "aerodynamics of
fixed-wing aircraft" touches lift generation, drag, stability, control surfaces, stall
behavior, airfoil selection, and more — each arguably deep enough to be its own topic). If
partway through research it becomes clear this is one of those broad topics, do NOT try to
brute-force full coverage of every sub-area in this one pass, and do NOT silently stop
short either. Instead: cover the core fundamentals solidly, then explicitly say so in your
final log_event description — name which sub-areas you covered and which ones would
benefit from their own dedicated research run (e.g. "this topic is broad; covered the core
fundamentals of X, but sub-topics like Y and Z would benefit from their own dedicated
research runs").

SURVEY THE REAL RANGE — this project's founding principle (CLAUDE.md) is that no
engineering solution is decided by default or because it's familiar; the agent ecosystem
discovers what actually works from evidence. This applies to research too. Where a topic
touches an open engineering decision (an approach with multiple real, competing solutions —
e.g. different aircraft configurations, different control architectures, different
structural approaches), do NOT research only the most common/familiar one and present it as
the answer. Actively search for and include less-common but well-evidenced alternatives too,
even ones that aren't the default choice. The goal is to arm the engineering agents with the
actual solution space, not a single reference design.

TURN BUDGET: you have a hard limit of {MAX_TURNS} conversation turns for this ENTIRE task —
searching, extracting, AND storing, all together. This is not optional, and the conversation
will be cut off the instant it's reached, with no chance afterward to do a final summary or
catch-up storage. Because of that, work INCREMENTALLY — do not search everything first and
store everything at the end; if you're cut off mid-way through that plan, everything you
found is lost. Instead, repeat this cycle per sub-area rather than batching:

1. Use WebSearch for ONE sub-area or angle of the topic at a time.
2. Immediately extract SPECIFIC, PRECISE facts from what you just found — exact numeric
   limits, thresholds, ratios, formulas, or specific named failure modes and their
   triggers. Do NOT write vague statements — every entry must contain a concrete number or
   a specific, falsifiable claim.
3. Immediately call upsert_kb for each distinct fact from that search, right away, before
   moving to the next sub-area — do not queue facts up to store later. If one source
   contains multiple genuinely distinct facts, create a SEPARATE entry for each rather than
   combining them into one paragraph.
   - entry_id: a unique, descriptive slug you generate (e.g. "{topic_tag}-<short-description>")
   - text: the specific fact itself, written precisely, in one or two sentences
   - topic: "{topic_tag}"
   - source_url: the real URL you found this in
   - source_title: the title/name of that source
4. Move to the next sub-area and repeat, roughly tracking how much of your turn budget
   you've used. If you sense you're running low, stop opening new sub-areas and make sure
   log_event (next step) gets called before you run out — even if that means covering less
   breadth than you'd like.
5. Call log_event ONCE, as close to the end as you can safely fit it in, with
   event_type="foundational_research" and a description summarizing how many entries you
   created, what topic was covered, and — if this topic turned out to be broad per the
   SCOPE guidance above — which sub-areas still need their own dedicated research runs. If
   you get cut off before reaching this step, whatever you already stored via upsert_kb
   still stands on its own — that's the whole point of storing incrementally.

Do not fabricate numbers or sources. If you can't verify a specific figure from a real
source, don't include it as a precise claim.
"""


async def research_topic(topic: str) -> dict:
    """Runs the full research flow for one topic.

    Returns a stats dict: cost, entries_created (counted from actual upsert_kb
    tool calls, not the agent's self-reported summary), and turns. Raises if
    the run itself errored out, so the caller can decide whether to retry.
    """
    topic_tag = slugify(topic)
    options = agent_runtime.build_options(
        system_prompt=(
            "You are the Foundational Research Agent from a multi-agent electric aircraft "
            "engineering project's Knowledge Base division. You must use real web search — "
            "never fabricate sources or numbers. Be thorough but precise."
        ),
        storage_server=storage_server,
        allowed_tools=ALLOWED_TOOLS,
        builtin_tools=["WebSearch"],  # the only built-in tool this agent needs
        max_turns=MAX_TURNS,
    )

    counts = {"entries_created": 0, "entries_skipped": 0}
    warned_long_run = False

    def count_entries(text: str) -> None:
        """Counted from real tool results, not the agent's self-reported summary."""
        if "[SKIP]" in text and "already exists" in text:
            counts["entries_skipped"] += 1
        elif "Stored KB entry" in text:
            counts["entries_created"] += 1

    def warn_if_running_long(turn: int) -> None:
        nonlocal warned_long_run
        if not warned_long_run and turn >= TURN_WARNING_THRESHOLD:
            warned_long_run = True
            print(
                f"  [!] WARNING: topic {topic!r} is running long — "
                f"~{turn} turns so far, approaching max_turns={MAX_TURNS}. "
                f"This topic may be broader than expected.",
                file=sys.stderr,
            )

    run_stats = await agent_runtime.run_agent(
        "FoundationalResearchAgent",
        options,
        build_prompt(topic, topic_tag),
        truncate=800,
        on_tool_result=count_entries,
        on_assistant_turn=warn_if_running_long,
    )

    stats = {**run_stats, **counts}
    # A max_turns cutoff on a broad topic is an expected outcome, not a bug --
    # whatever was found is already safely stored (incremental storage, above).
    # Retrying would just re-run the same broad topic into the same ceiling
    # again, wasting cost for no gain; only treat genuinely unexpected errors
    # as retry-worthy.
    if stats["is_error"] and not stats["hit_turn_limit"]:
        raise RuntimeError(f"agent run for topic {topic!r} errored")
    return stats


async def research_topic_with_retry(topic: str, retries: int = 1) -> dict:
    """Runs research_topic, retrying transient failures up to `retries` times.

    Never raises — a topic that still fails after retries comes back with
    status='failed' so the caller can continue on to the rest of the batch.
    """
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            stats = await research_topic(topic)
            status = "partial" if stats.get("hit_turn_limit") else "ok"
            stats.update(topic=topic, status=status)
            return stats
        except Exception as exc:  # noqa: BLE001 — deliberately broad: any failure should be retried/reported, not crash the batch
            last_error = exc
            print(f"  [!] topic {topic!r} attempt {attempt + 1} failed: {exc}", file=sys.stderr)
    return {
        "topic": topic,
        "status": "failed",
        "cost": 0.0,
        "entries_created": 0,
        "entries_skipped": 0,
        "turns": 0,
        "error": str(last_error),
    }


async def main():
    parser = argparse.ArgumentParser(description="Foundational Research Agent")
    parser.add_argument("--topic", action="append", default=[], help="Research a topic (repeatable for multiple)")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Include all six foundational topics from CLAUDE.md (combine with --topic to add more)",
    )
    args = parser.parse_args()

    topics = (CORE_TOPICS if args.all else []) + args.topic
    seen = set()
    topics = [t for t in topics if not (t in seen or seen.add(t))]
    if not topics:
        parser.error('Pass --topic "..." (repeatable) and/or --all')

    results = []
    for topic in topics:
        print(f"\n===== TOPIC: {topic} =====")
        results.append(await research_topic_with_retry(topic))

    total_cost = sum(r["cost"] for r in results)
    total_entries = sum(r["entries_created"] for r in results)
    total_skipped = sum(r.get("entries_skipped", 0) for r in results)
    failed = [r for r in results if r["status"] == "failed"]
    partial = [r for r in results if r["status"] == "partial"]

    print(f"\n===== SUMMARY — {len(topics)} topic(s) =====")
    for r in results:
        if r["status"] == "ok":
            status_line = "OK"
        elif r["status"] == "partial":
            status_line = "PARTIAL (hit turn limit — narrower follow-up topic recommended)"
        else:
            status_line = f"FAILED ({r.get('error')})"
        skipped_str = f", skipped={r['entries_skipped']}" if r.get("entries_skipped") else ""
        print(f"  - {r['topic']}: {status_line}, created={r['entries_created']}{skipped_str}, cost=${r['cost']:.4f}")
    print(
        f"Total: {total_entries} created, {total_skipped} skipped, ${total_cost:.4f} spent, "
        f"{len(partial)} topic(s) partial, {len(failed)} topic(s) failed"
    )


if __name__ == "__main__":
    anyio.run(main)
