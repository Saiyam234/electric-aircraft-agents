"""Shared runtime for every agent: options construction + the streaming loop.

Before this existed, each agent duplicated ~60 lines — the ClaudeAgentOptions
block, the three-branch message loop, and run tracking. At the 19 agents
CLAUDE.md calls for that's ~1100 duplicated lines and 19 separate places to
fix any future bug.

More importantly, it makes CLAUDE.md's MCP security rule structural instead
of a copy-paste convention. `tools` and `strict_mcp_config=True` are set here,
once, rather than being retyped in every agent and silently omitted in one.
That omission is not hypothetical: it actually happened during the KB Manager
build and exposed the full user-level MCP config (Gmail, Calendar, Drive) to
a spawned agent. Going through build_options() makes that failure mode
unreachable by construction.
"""

from __future__ import annotations

import sys
from typing import Any, Callable

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
)

DEFAULT_MAX_TURNS = 20
DEFAULT_RESULT_TRUNCATE = 1000


def build_options(
    *,
    system_prompt: str,
    storage_server: Any,
    allowed_tools: list[str],
    builtin_tools: list[str] | None = None,
    max_turns: int = DEFAULT_MAX_TURNS,
) -> ClaudeAgentOptions:
    """Builds ClaudeAgentOptions with the non-negotiable security settings baked in.

    `builtin_tools` is the allowlist of Claude's own built-in tools (e.g.
    ["WebSearch"]). It defaults to [] — no Bash/Read/Write/etc. Pass only what
    an agent genuinely needs.

    Note `allowed_tools` alone does NOT restrict what an agent can see; it only
    pre-approves specific tools so they don't prompt. Restricting visibility is
    what `tools` and `strict_mcp_config` do, which is why they're forced here.
    """
    return ClaudeAgentOptions(
        mcp_servers={"storage": storage_server},
        tools=list(builtin_tools or []),
        allowed_tools=allowed_tools,
        strict_mcp_config=True,
        system_prompt=system_prompt,
        max_turns=max_turns,
        permission_mode="bypassPermissions",
    )


async def run_agent(
    agent_name: str,
    options: ClaudeAgentOptions,
    prompt: str,
    *,
    truncate: int | None = DEFAULT_RESULT_TRUNCATE,
    on_tool_result: Callable[[str], None] | None = None,
    on_assistant_turn: Callable[[int], None] | None = None,
) -> dict:
    """Runs one agent conversation to completion, printing progress as it goes.

    Brackets the run with storage.log_run_start/log_run_end so it's traceable
    in the audit log via a shared run_id.

    `on_tool_result` is called with each raw tool-result string BEFORE it's
    truncated for display — that ordering matters, since counters built on
    result text (e.g. counting stored vs. skipped KB entries) would otherwise
    miss anything past the truncation point.

    `on_assistant_turn` is called with the running count of assistant messages,
    for agents that track how much of their turn budget they've consumed and
    warn before hitting the ceiling.

    Returns {"cost", "turns", "is_error", "hit_turn_limit"}. Does not raise on
    an errored run — the caller decides what a failure means, since for some
    agents hitting the turn limit is an expected outcome rather than a bug.
    """
    stats = {"cost": 0.0, "turns": 0, "is_error": False, "hit_turn_limit": False}
    assistant_turns = 0
    run_id = storage.log_run_start(agent_name)

    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                assistant_turns += 1
                if on_assistant_turn is not None:
                    on_assistant_turn(assistant_turns)
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(block.text)
                    elif isinstance(block, ToolUseBlock):
                        print(f"  [calling] {block.name}({block.input})")
            elif isinstance(message, UserMessage):
                for block in message.content:
                    if isinstance(block, ToolResultBlock):
                        text = str(block.content)
                        if on_tool_result is not None:
                            on_tool_result(text)
                        if truncate is not None and len(text) > truncate:
                            text = text[:truncate] + " ...[truncated]"
                        print(f"  [result]  {text}")
            elif isinstance(message, ResultMessage):
                stats["cost"] = message.total_cost_usd or 0.0
                stats["turns"] = message.num_turns
                stats["is_error"] = message.is_error
                stats["hit_turn_limit"] = message.terminal_reason == "max_turns"
                print(
                    f"\n--- {agent_name}: turns={message.num_turns} cost=${stats['cost']:.4f} "
                    f"error={message.is_error} terminal_reason={message.terminal_reason} ---"
                )
                storage.log_run_end(agent_name, run_id, message.num_turns, stats["cost"])
                if message.is_error:
                    print(message.result, file=sys.stderr)

    return stats
