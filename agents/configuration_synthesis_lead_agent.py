"""Configuration Synthesis Lead (Concurrent Engineering Cluster, per CLAUDE.md).

Owns the overall aircraft configuration: dimensions, wing loading, power
loading, general arrangement, weight & balance. Also the cluster's standing
tiebreaker — though there is nothing to arbitrate yet, since the rest of the
cluster doesn't exist.

WAVE 1 SCOPE — deliberately does NOT select the VTOL architecture.

CLAUDE.md does put architecture selection inside this cluster's remit. But the
cluster is defined as "one continuously-messaging team," and right now the
Airframe Engineer, Propulsion & Power Engineer, and Chief Integration Agent
that would push back on a bad choice don't exist. Letting this agent pick an
architecture alone, unchallenged, is precisely the "defaulted toward a
reference design because it's familiar" failure the founding principle exists
to prevent.

So wave 1 produces: a sizing envelope that holds regardless of architecture,
plus an evidence-backed comparison of the candidate architectures with the
selection explicitly left OPEN. The pick happens once the cluster can actually
argue about it.

Usage:
    python3 -m agents.configuration_synthesis_lead_agent
"""

import argparse
import json
import time

import anyio

import agent_runtime
import storage
from claude_agent_sdk import create_sdk_mcp_server, tool

AGENT_NAME = "ConfigurationSynthesisLead"


@tool("search_kb", "Semantic search the knowledge base for evidence to ground a design number", {"query": str})
async def search_kb_tool(args):
    matches = storage.search_kb(args["query"], top_k=5)
    trimmed = [
        {
            "id": m["id"],
            "text": m["metadata"].get("text", ""),
            "source_title": m["metadata"].get("source_title", ""),
        }
        for m in matches
    ]
    return {"content": [{"type": "text", "text": json.dumps(trimmed, default=str)}]}


@tool("list_requirements", "List the requirements this configuration has to satisfy", {})
async def list_requirements_tool(args):
    rows = storage.list_requirements(limit=100)
    return {"content": [{"type": "text", "text": json.dumps(rows, default=str)}]}


@tool("list_baselines", "List existing baselines, to see what configurations already exist", {})
async def list_baselines_tool(args):
    return {"content": [{"type": "text", "text": json.dumps(storage.list_baselines(limit=50), default=str)}]}


@tool(
    "record_configuration",
    "Record the configuration as a draft baseline. config_json must be a JSON object string.",
    {"config_json": str},
)
async def record_configuration_tool(args):
    try:
        config = json.loads(args["config_json"])
    except json.JSONDecodeError as exc:
        return {
            "content": [{"type": "text", "text": f"[REJECTED] config_json is not valid JSON: {exc}"}],
            "is_error": True,
        }
    if not isinstance(config, dict):
        return {
            "content": [{"type": "text", "text": "[REJECTED] config_json must be a JSON object, not a list or scalar"}],
            "is_error": True,
        }

    # Version generated here, not by the model — deterministic and collision-free.
    version = f"v0.1-config-draft-{int(time.time())}"
    try:
        baseline_id = storage.create_baseline(config, version=version)
    except (TypeError, ValueError) as exc:
        return {"content": [{"type": "text", "text": f"[REJECTED] baseline not created: {exc}"}], "is_error": True}
    return {
        "content": [
            {"type": "text", "text": f"Recorded draft baseline id={baseline_id} version={version} (status=draft)"}
        ]
    }


@tool("log_event", "Log a summary event to the audit log", {"event_type": str, "description": str})
async def log_event_tool(args):
    storage.log_event(AGENT_NAME, args["event_type"], args["description"])
    return {"content": [{"type": "text", "text": "Logged event"}]}


storage_server = create_sdk_mcp_server(
    name="storage",
    tools=[
        search_kb_tool,
        list_requirements_tool,
        list_baselines_tool,
        record_configuration_tool,
        log_event_tool,
    ],
)

ALLOWED_TOOLS = [
    "mcp__storage__search_kb",
    "mcp__storage__list_requirements",
    "mcp__storage__list_baselines",
    "mcp__storage__record_configuration",
    "mcp__storage__log_event",
]

PROMPT = """You are the Configuration Synthesis Lead for a multi-agent electric aircraft
engineering project. You own the overall aircraft configuration: dimensions, wing loading,
power loading, general arrangement, weight & balance.

The aircraft is a 1:8-scale, electric, fully autonomous eVTOL (vertical takeoff and landing
is required). It follows a pre-set waypoint plan on its own — no remote pilot.

Steps:
1. Call list_requirements to see what this configuration must satisfy.
2. Call list_baselines to see what already exists (expect only test artifacts).
3. Use search_kb repeatedly to ground your numbers in real evidence. The knowledge base has
   cited research on wing loading, stall speed, aspect-ratio trades, airfoil data, battery
   limits, and composite structures. Pull real figures rather than estimating from memory.
4. Call record_configuration ONCE with your configuration as a JSON object.
5. Call log_event ONCE with event_type="configuration_drafted" summarizing what you set,
   what you left open, and what most needs challenging by other agents.

WHAT THE CONFIGURATION SHOULD CONTAIN:
A JSON object with, at minimum: overall dimensions (wingspan, wing area, length), estimated
mass budget broken down by major group (structure / battery / propulsion / avionics /
payload), wing loading, an estimated cruise and stall speed, and a rough power/energy
estimate. For every number, include how you arrived at it — a parallel "rationale" or
"basis" field naming the knowledge-base evidence or the calculation behind it. A number with
no traceable basis is worse than no number.

CRITICAL — DO NOT SELECT THE VTOL ARCHITECTURE:
Do NOT pick tiltrotor, tiltwing, lift+cruise, tailsitter, or any other specific VTOL
architecture. That decision is explicitly reserved until the rest of the engineering cluster
exists to challenge it — the Airframe Engineer and Propulsion & Power Engineer who would
argue against a bad choice have not been built yet, and an unchallenged pick here is exactly
how a project ends up defaulting to whatever design is most familiar.

Instead:
- Make the sizing envelope as architecture-agnostic as you can, and say which numbers would
  shift once an architecture is chosen.
- Include an "architecture_candidates" section: for each realistic candidate, give the real
  evidence-backed advantages and disadvantages AT THIS SCALE, and what specific open
  question would decide between them.
- Set an explicit field marking the architecture as not yet selected.

Do not invent numbers. Where the evidence doesn't support a figure, say so and mark it as
to-be-determined rather than fabricating something that looks precise.
"""


async def main():
    argparse.ArgumentParser(description="Configuration Synthesis Lead — initial configuration pass").parse_args()

    options = agent_runtime.build_options(
        system_prompt=(
            "You are the Configuration Synthesis Lead from a multi-agent electric aircraft "
            "engineering project. Every number you set must be traceable to evidence or an "
            "explicit calculation. Be precise and concrete — never fabricate a figure."
        ),
        storage_server=storage_server,
        allowed_tools=ALLOWED_TOOLS,
        max_turns=40,
    )

    stats = await agent_runtime.run_agent(AGENT_NAME, options, PROMPT)
    print(f"\n===== DONE — cost ${stats['cost']:.4f} =====")


if __name__ == "__main__":
    anyio.run(main)
