"""Proves storage.py works end to end when driven by a real Claude agent
(via the Claude Agent SDK), not just direct function calls.

Wraps storage.py's functions as in-process SDK MCP tools, then gives Claude
a prompt walking through: add a requirement, create a baseline, get all
three Assurance Gate sign-offs, confirm it's stamped, store a KB entry, and
find it again via semantic search.
"""

import json
import time

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


@tool("add_requirement", "Add a requirement to the requirements table", {"text": str})
async def add_requirement_tool(args):
    req_id = storage.add_requirement(args["text"])
    return {"content": [{"type": "text", "text": f"Created requirement id={req_id}"}]}


@tool(
    "create_baseline",
    "Create a new baseline. config_json is a JSON string, version must be unique",
    {"config_json": str, "version": str},
)
async def create_baseline_tool(args):
    config = json.loads(args["config_json"])
    baseline_id = storage.create_baseline(config, version=args["version"])
    return {"content": [{"type": "text", "text": f"Created baseline id={baseline_id} version={args['version']}"}]}


@tool(
    "record_signoff",
    "Record an Assurance Gate office sign-off. office must be review_critic, safety_risk, or regulatory",
    {"baseline_id": float, "office": str, "notes": str},
)
async def record_signoff_tool(args):
    storage.record_signoff(int(args["baseline_id"]), args["office"], args.get("notes", ""))
    return {"content": [{"type": "text", "text": f"Recorded {args['office']} sign-off on baseline_id={int(args['baseline_id'])}"}]}


@tool("is_baseline_stamped", "Check whether all three Assurance offices have signed off a baseline", {"baseline_id": float})
async def is_baseline_stamped_tool(args):
    stamped = storage.is_baseline_stamped(int(args["baseline_id"]))
    return {"content": [{"type": "text", "text": f"stamped={stamped}"}]}


@tool("upsert_kb", "Store a piece of text in the semantic knowledge base", {"entry_id": str, "text": str})
async def upsert_kb_tool(args):
    storage.upsert_kb(args["entry_id"], args["text"])
    # Vectorize is eventually consistent — a freshly-upserted vector isn't
    # guaranteed searchable immediately, so give indexing a moment before
    # any follow-up search_kb call.
    time.sleep(8)
    return {"content": [{"type": "text", "text": f"Stored KB entry id={args['entry_id']}"}]}


@tool("search_kb", "Semantic search over the knowledge base", {"query": str})
async def search_kb_tool(args):
    results = storage.search_kb(args["query"], top_k=3)
    return {"content": [{"type": "text", "text": json.dumps(results)}]}


storage_server = create_sdk_mcp_server(
    name="storage",
    tools=[
        add_requirement_tool,
        create_baseline_tool,
        record_signoff_tool,
        is_baseline_stamped_tool,
        upsert_kb_tool,
        search_kb_tool,
    ],
)

ALLOWED_TOOLS = [
    "mcp__storage__add_requirement",
    "mcp__storage__create_baseline",
    "mcp__storage__record_signoff",
    "mcp__storage__is_baseline_stamped",
    "mcp__storage__upsert_kb",
    "mcp__storage__search_kb",
]

PROMPT = """Run this exact sequence against the storage tools, in order, waiting for
each result before moving to the next step:

1. Call add_requirement with text "Autopilot shall maintain altitude within +/-2m in cruise".
2. Call create_baseline with config_json '{"wingspan_mm": 1500, "note": "agent-sdk-test"}'
   and a version string that is unique by including the current unix-time-like number you
   make up, e.g. "v-agent-test-<random digits>".
3. Call record_signoff three times on that same baseline_id: once each for
   office="review_critic", office="safety_risk", office="regulatory".
4. Call is_baseline_stamped on that baseline_id.
5. Call upsert_kb with a unique entry_id like "agent-test-<random digits>" and text
   "Carbon fiber spars reduce structural weight while maintaining stiffness for small electric aircraft".
6. Call search_kb with query "lightweight composite structural materials" and check whether
   the entry_id from step 5 appears in the results.

After all 6 steps, print a line for each step formatted exactly as:
STEP 1: PASS or STEP 1: FAIL (with a one-line reason)
...through STEP 6, based on the actual tool results you received (e.g. step 4 is PASS only
if stamped=True, step 6 is PASS only if your step-5 entry_id is present in the search results).
"""


async def main():
    options = ClaudeAgentOptions(
        mcp_servers={"storage": storage_server},
        tools=[],  # no built-in tools (Bash/Read/Write/etc.) — only the storage MCP tools below
        allowed_tools=ALLOWED_TOOLS,
        strict_mcp_config=True,  # ignore any user/project MCP config — only the server passed above
        system_prompt=(
            "You are a test agent verifying the electric-aircraft-agents storage layer. "
            "Use only the provided storage tools to complete the task. Be concise."
        ),
        max_turns=20,
        permission_mode="bypassPermissions",
    )

    run_id = storage.log_run_start("TestAgent")
    async with ClaudeSDKClient(options=options) as client:
        await client.query(PROMPT)
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
                print(f"\n--- turns={message.num_turns} cost=${message.total_cost_usd:.4f} error={message.is_error} ---")
                storage.log_run_end("TestAgent", run_id, message.num_turns, message.total_cost_usd or 0.0)


if __name__ == "__main__":
    anyio.run(main)
