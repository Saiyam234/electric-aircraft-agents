"""Foundational Research Agent (Knowledge Base division, per CLAUDE.md).

Proactively builds the reference library using REAL web search — not
synthesis from the model's own training knowledge. Each distinct fact found
gets its own knowledge-base entry (via storage.upsert_kb) tagged with topic
and source metadata, so it stays precise and individually searchable later.
One research event is logged via storage.log_event per topic when done.

Usage:
    python3 foundational_research_agent.py --topic "structural materials"
    python3 foundational_research_agent.py --topic "X" --topic "Y"   # multiple custom topics
    python3 foundational_research_agent.py --all                    # the 6 CLAUDE.md topics
    python3 foundational_research_agent.py --all --topic "extra one" # all 6 plus a custom one

Each topic runs in its own conversation. If a topic's run errors out, it's
retried once; if it still fails, that topic is marked failed and the batch
continues with the remaining topics rather than aborting the whole run.
"""

import argparse
import re
import sys

import anyio
import storage
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    create_sdk_mcp_server,
    tool,
)

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
    storage.upsert_kb(
        args["entry_id"],
        args["text"],
        metadata={
            "topic": args["topic"],
            "source_url": args["source_url"],
            "source_title": args["source_title"],
        },
    )
    return {"content": [{"type": "text", "text": f"Stored KB entry id={args['entry_id']}"}]}


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

Steps:
1. Use WebSearch to find real sources on this topic (technical articles, manufacturer
   datasheets, standards documents, published papers, established guides — whatever has
   real numbers). Do several distinct searches to cover the topic's real breadth, not just
   one narrow angle of it.
2. From what you find, extract SPECIFIC, PRECISE data points an engineer would actually
   use — exact numeric limits, thresholds, ratios, formulas, or specific named failure
   modes and their triggers. Do NOT write vague statements — every entry must contain a
   concrete number or a specific, falsifiable claim.
3. If one source contains multiple genuinely distinct important facts, create a SEPARATE
   knowledge base entry for each distinct fact rather than combining them into one
   paragraph, so each stays precise and individually searchable.
4. For every fact, call the upsert_kb tool with:
   - entry_id: a unique, descriptive slug you generate (e.g. "{topic_tag}-<short-description>")
   - text: the specific fact itself, written precisely, in one or two sentences
   - topic: "{topic_tag}"
   - source_url: the real URL you found this in
   - source_title: the title/name of that source
5. When done, call log_event ONCE with event_type="foundational_research" and a description
   summarizing how many entries you created, what topic was covered, and — if this topic
   turned out to be broad per the SCOPE guidance above — which sub-areas still need their
   own dedicated research runs.

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
    options = ClaudeAgentOptions(
        mcp_servers={"storage": storage_server},
        allowed_tools=ALLOWED_TOOLS,
        system_prompt=(
            "You are the Foundational Research Agent from a multi-agent electric aircraft "
            "engineering project's Knowledge Base division. You must use real web search — "
            "never fabricate sources or numbers. Be thorough but precise."
        ),
        max_turns=MAX_TURNS,
        permission_mode="bypassPermissions",
    )

    stats = {"cost": 0.0, "entries_created": 0, "turns": 0}
    approx_turns = 0
    warned_long_run = False
    async with ClaudeSDKClient(options=options) as client:
        await client.query(build_prompt(topic, topic_tag))
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                approx_turns += 1
                if not warned_long_run and approx_turns >= TURN_WARNING_THRESHOLD:
                    warned_long_run = True
                    print(
                        f"  [!] WARNING: topic {topic!r} is running long — "
                        f"~{approx_turns} turns so far, approaching max_turns={MAX_TURNS}. "
                        f"This topic may be broader than expected.",
                        file=sys.stderr,
                    )
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(block.text)
                    elif isinstance(block, ToolUseBlock):
                        print(f"  [calling] {block.name}({block.input})")
                        if block.name == "mcp__storage__upsert_kb":
                            stats["entries_created"] += 1
            elif isinstance(message, UserMessage):
                for block in message.content:
                    if isinstance(block, ToolResultBlock):
                        text = str(block.content)
                        if len(text) > 800:
                            text = text[:800] + " ...[truncated]"
                        print(f"  [result]  {text}")
            elif isinstance(message, ResultMessage):
                stats["cost"] = message.total_cost_usd or 0.0
                stats["turns"] = message.num_turns
                print(
                    f"\n--- topic={topic!r} turns={message.num_turns} "
                    f"cost=${stats['cost']:.4f} error={message.is_error} ---"
                )
                if message.is_error:
                    raise RuntimeError(f"agent run for topic {topic!r} errored: {message.result}")
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
            stats.update(topic=topic, status="ok")
            return stats
        except Exception as exc:  # noqa: BLE001 — deliberately broad: any failure should be retried/reported, not crash the batch
            last_error = exc
            print(f"  [!] topic {topic!r} attempt {attempt + 1} failed: {exc}", file=sys.stderr)
    return {"topic": topic, "status": "failed", "cost": 0.0, "entries_created": 0, "turns": 0, "error": str(last_error)}


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
    failed = [r for r in results if r["status"] == "failed"]

    print(f"\n===== SUMMARY — {len(topics)} topic(s) =====")
    for r in results:
        status_line = "OK" if r["status"] == "ok" else f"FAILED ({r.get('error')})"
        print(f"  - {r['topic']}: {status_line}, entries={r['entries_created']}, cost=${r['cost']:.4f}")
    print(f"Total: {total_entries} entries created, ${total_cost:.4f} spent, {len(failed)} topic(s) failed")


if __name__ == "__main__":
    anyio.run(main)
