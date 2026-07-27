"""MCP tools shared by more than one agent.

Kept separate from agent_runtime.py (which runs conversations) and from
engineering_math.py (which stays pure math with no SDK dependency, so it can be
tested instantly and offline).

The calculate tool in particular exists here rather than inside one agent
because the first real Wave 1 run showed why: the agent that had a calculator
used it correctly, and the agent that didn't have one silently did arithmetic
in prose instead. Any agent that emits numbers gets this tool.
"""

import json

from claude_agent_sdk import tool

import engineering_math
import storage


@tool(
    "calculate",
    "Run an exact engineering calculation in Python. formula is a name from the list in your "
    "prompt; params_json is a JSON object of its arguments. Always use this instead of working "
    "a number out yourself.",
    {"formula": str, "params_json": str},
)
async def calculate_tool(args):
    try:
        params = json.loads(args["params_json"])
    except json.JSONDecodeError as exc:
        return {
            "content": [{"type": "text", "text": f"[REJECTED] params_json is not valid JSON: {exc}"}],
            "is_error": True,
        }

    outcome = engineering_math.calculate(args["formula"], params)
    if not outcome["ok"]:
        return {"content": [{"type": "text", "text": f"[REJECTED] {outcome['error']}"}], "is_error": True}

    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps({"formula": args["formula"], "inputs": params, "result": outcome["result"]}),
            }
        ]
    }


@tool("search_kb", "Semantic search the knowledge base for cited evidence", {"query": str})
async def search_kb_tool(args):
    matches = storage.search_kb(args["query"], top_k=5)
    trimmed = [
        {
            "id": m["id"],
            "text": m["metadata"].get("text", ""),
            "source_title": m["metadata"].get("source_title", ""),
            "source_url": m["metadata"].get("source_url", ""),
        }
        for m in matches
    ]
    return {"content": [{"type": "text", "text": json.dumps(trimmed, default=str)}]}


def make_log_event_tool(agent_name: str):
    """Factory — the audit log records which agent acted, so the name has to be
    bound per agent rather than passed by the model (which could then misreport
    who did what)."""

    @tool("log_event", "Log a summary event to the audit log", {"event_type": str, "description": str})
    async def log_event_tool(args):
        storage.log_event(agent_name, args["event_type"], args["description"])
        return {"content": [{"type": "text", "text": "Logged event"}]}

    return log_event_tool
