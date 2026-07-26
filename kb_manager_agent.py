"""KB Manager agent (Knowledge Base division, per CLAUDE.md).

Full job per CLAUDE.md: spawn dynamic research agents for narrower topics,
reconcile/deduplicate all findings, tag facts for findability, validate facts
to citable status, version everything by baseline, and record rejected
ideas/lessons-learned.

This first pass covers reconciliation + citation validation only, run
against the REAL entries already in the KB from Foundational Research Agent
runs — no synthetic test data:

1. Fetch every entry currently in the KB.
2. Deterministically (no LLM) compute pairwise cosine similarity between all
   entries' embeddings, to surface CANDIDATE near-duplicate/overlapping
   pairs. This is a math problem, not a judgment problem, so it's done in
   plain Python rather than asked of the model.
3. Deterministically check each entry has a non-empty source_url.
4. Hand the candidate pairs to a real agent conversation for judgment: is
   this pair a true duplicate/overlap worth flagging, or just topically
   similar but genuinely distinct facts (which raw cosine similarity alone
   can't reliably tell apart)? Entries are never silently merged — findings
   are only flagged for human review.
5. Log one summary event via storage.log_event.

At this KB size (dozens of entries), fetching everything and handing it to
one conversation is fine. This would need reworking (batching, incremental
review) once the KB grows much larger.
"""

import argparse
import sys
from itertools import combinations

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

SIMILARITY_THRESHOLD = 0.85  # pairs at/above this are passed to the agent for judgment
MAX_CANDIDATE_PAIRS = 40  # keeps the prompt bounded even if many entries cluster tightly


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def find_candidate_duplicate_pairs(entries: list[dict]) -> list[dict]:
    pairs = []
    for a, b in combinations(entries, 2):
        sim = _cosine_similarity(a["values"], b["values"])
        if sim >= SIMILARITY_THRESHOLD:
            pairs.append(
                {
                    "id_a": a["id"],
                    "text_a": a["metadata"].get("text", ""),
                    "id_b": b["id"],
                    "text_b": b["metadata"].get("text", ""),
                    "similarity": round(sim, 4),
                }
            )
    pairs.sort(key=lambda p: p["similarity"], reverse=True)
    return pairs[:MAX_CANDIDATE_PAIRS]


def validate_citations(entries: list[dict]) -> dict:
    passed, failed = [], []
    for e in entries:
        url = (e["metadata"].get("source_url") or "").strip()
        (passed if url else failed).append(e["id"])
    return {"passed": passed, "failed": failed}


@tool("log_event", "Log a KB reconciliation event to the audit log", {"event_type": str, "description": str})
async def log_event_tool(args):
    storage.log_event("KBManager", args["event_type"], args["description"])
    return {"content": [{"type": "text", "text": "Logged event"}]}


storage_server = create_sdk_mcp_server(name="storage", tools=[log_event_tool])
ALLOWED_TOOLS = ["mcp__storage__log_event"]


def build_prompt(entries: list[dict], candidate_pairs: list[dict], citation_results: dict) -> str:
    entries_summary = "\n".join(
        f'- id="{e["id"]}" topic="{e["metadata"].get("topic")}" text="{e["metadata"].get("text")}"' for e in entries
    )
    pairs_summary = "\n".join(
        f'{i + 1}. similarity={p["similarity"]}\n   A: id="{p["id_a"]}" text="{p["text_a"]}"\n'
        f'   B: id="{p["id_b"]}" text="{p["text_b"]}"'
        for i, p in enumerate(candidate_pairs)
    )
    if not pairs_summary:
        pairs_summary = "(none — no pair of entries scored above the similarity threshold)"

    return f"""You are the KB Manager for a multi-agent electric aircraft engineering project.
Your job right now: reconcile the knowledge base by reviewing candidate near-duplicate/
overlapping entries, and report on citation validation. You do NOT merge or delete
anything — you only flag findings for human review.

ALL {len(entries)} ENTRIES CURRENTLY IN THE KB:
{entries_summary}

CANDIDATE DUPLICATE/OVERLAP PAIRS (found by cosine similarity >= {SIMILARITY_THRESHOLD},
top {MAX_CANDIDATE_PAIRS} shown; this is a MATH-based candidate list, not a judgment —
your job is to apply real judgment to each one):
{pairs_summary}

CITATION VALIDATION (already computed deterministically — non-empty source_url required):
- {len(citation_results['passed'])} entries PASSED (have a source_url): {citation_results['passed']}
- {len(citation_results['failed'])} entries FAILED (missing/empty source_url): {citation_results['failed']}

Your tasks:
1. For each candidate pair above, decide one of:
   - TRUE_DUPLICATE: same underlying fact, just reworded or re-inserted (e.g. literally the
     same claim from repeated test runs)
   - OVERLAP: related/adjacent facts worth a human glancing at together, but each contains
     distinct information (e.g. different specific figures, different named items) — not a
     duplicate, just close enough that a human should confirm they're both worth keeping
   - FALSE_POSITIVE: not actually related — the embedding similarity was a coincidence of
     phrasing/topic, the facts themselves are unrelated
   Do not merge or recommend deleting anything — just classify each pair with a one-line
   reason.
2. Report the citation validation results (pass through the numbers above, they're already
   computed correctly).
3. Call log_event ONCE with event_type="kb_reconciliation" and a description summarizing:
   total entries reviewed, how many pairs were TRUE_DUPLICATE / OVERLAP / FALSE_POSITIVE,
   and the citation validation pass/fail counts.

Then give a clear final summary of your classifications for every candidate pair.
"""


async def main():
    parser = argparse.ArgumentParser(description="KB Manager — reconciliation + citation validation pass")
    parser.parse_args()

    print("Fetching all KB entries...")
    ids = storage.list_kb_ids()
    entries = storage.get_kb_entries(ids)
    print(f"Fetched {len(entries)} entries.")

    print("Computing pairwise similarity (local, no API cost)...")
    candidate_pairs = find_candidate_duplicate_pairs(entries)
    print(f"Found {len(candidate_pairs)} candidate pair(s) at similarity >= {SIMILARITY_THRESHOLD}.")

    print("Validating citations (local, no API cost)...")
    citation_results = validate_citations(entries)
    print(f"Citations: {len(citation_results['passed'])} passed, {len(citation_results['failed'])} failed.")

    options = ClaudeAgentOptions(
        mcp_servers={"storage": storage_server},
        tools=[],  # no built-in tools (Bash/Read/Write/etc.) — only the storage MCP tool below
        allowed_tools=ALLOWED_TOOLS,
        strict_mcp_config=True,  # ignore any user/project MCP config — only the server passed above
        system_prompt=(
            "You are the KB Manager from a multi-agent electric aircraft engineering "
            "project's Knowledge Base division. You reconcile and flag — you never "
            "silently merge or delete data. Be precise and concise."
        ),
        max_turns=20,
        permission_mode="bypassPermissions",
    )

    cost = 0.0
    async with ClaudeSDKClient(options=options) as client:
        await client.query(build_prompt(entries, candidate_pairs, citation_results))
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(block.text)
                    elif isinstance(block, ToolUseBlock):
                        print(f"  [calling] {block.name}({block.input})")
            elif isinstance(message, UserMessage):
                for block in message.content:
                    if isinstance(block, ToolResultBlock):
                        print(f"  [result]  {block.content}")
            elif isinstance(message, ResultMessage):
                cost = message.total_cost_usd or 0.0
                print(f"\n--- turns={message.num_turns} cost=${cost:.4f} error={message.is_error} ---")
                if message.is_error:
                    print(message.result, file=sys.stderr)

    print(f"\n===== DONE — {len(entries)} entries reviewed, {len(candidate_pairs)} candidate pairs, cost ${cost:.4f} =====")


if __name__ == "__main__":
    anyio.run(main)
