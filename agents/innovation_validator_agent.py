"""Innovation Validator — Wave 3, Innovation division (CLAUDE.md).

Per CLAUDE.md: "runs a fast feasibility check with Engineering, validates
each proposed innovation against Knowledge Base evidence + Math & Physics +
formal requirements, and packages proven innovations for handoff to the
Concurrent Engineering Cluster."

REAL DATA THIS IS TESTED AGAINST RIGHT NOW: there is no dynamic Innovation
field agent yet (CLAUDE.md's roster includes them but none are built), so
there is no live stream of proposed innovations to validate. Rather than
fabricate a candidate, this agent's self-test validates a real, already-
computed finding sitting inside baseline 89's own config: the
"hover_power_bracket" section shows real calculate()-derived hover power at
three rotor sizes (0.25 m, 0.40 m, 0.55 m) and states "larger discs are
strongly favored energetically." The self-test asks the agent to validate
"increase rotor diameter toward the 0.55 m case to ease the hover-dominated
energy budget" as a candidate innovation, using the SAME real baseline data,
independently re-run through calculate() rather than trusted from the
baseline text.

WHAT IT WILL NEED ONCE AVAILABLE: real dynamic field-agent output (proposed
innovations from a battery-efficiency or aerodynamic-efficiency field agent,
neither of which exist yet) to validate against, instead of a self-test
grounded in an existing baseline's own numbers.
"""

import argparse
import json

import anyio
from claude_agent_sdk import create_sdk_mcp_server, tool

import agent_runtime
import agent_tools
import engineering_math
import storage

AGENT_NAME = "InnovationValidator"

VALID_VERDICTS = {"PROVEN", "NOT_PROVEN", "NEEDS_MORE_RESEARCH"}


@tool(
    "list_baselines",
    "List recent baselines",
    {"limit": float},
)
async def list_baselines_tool(args):
    rows = storage.list_baselines(limit=int(args.get("limit", 10) or 10))
    return {"content": [{"type": "text", "text": json.dumps(rows, default=str)}]}


@tool(
    "get_baseline",
    "Get one baseline's full config by id",
    {"baseline_id": float},
)
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
    "record_innovation_verdict",
    "Record ONE verdict on a candidate innovation. verdict must be exactly "
    "PROVEN, NOT_PROVEN or NEEDS_MORE_RESEARCH.",
    {
        "innovation": str,
        "verdict": str,
        "kb_evidence": str,
        "math_check": str,
        "requirement_alignment": str,
        "rationale": str,
    },
)
async def record_innovation_verdict_tool(args):
    verdict = args["verdict"].strip().upper()
    if verdict not in VALID_VERDICTS:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"[REJECTED] verdict must be one of {sorted(VALID_VERDICTS)}, got "
                    f"{args['verdict']!r}. 'Looks promising' is not a verdict.",
                }
            ],
            "is_error": True,
        }
    # PROVEN specifically requires the two forms of real evidence CLAUDE.md
    # names (KB + Math & Physics) to actually be present, not just asserted —
    # a verdict of PROVEN with an empty evidence field is a contradiction.
    if verdict == "PROVEN" and (not args["kb_evidence"].strip() or not args["math_check"].strip()):
        return {
            "content": [
                {
                    "type": "text",
                    "text": "[REJECTED] PROVEN requires both kb_evidence and math_check to be "
                    "non-empty — requirement alignment alone is not proof.",
                }
            ],
            "is_error": True,
        }

    description = (
        f"INNOVATION: {args['innovation']} | VERDICT: {verdict} | "
        f"KB_EVIDENCE: {args['kb_evidence']} | MATH_CHECK: {args['math_check']} | "
        f"REQUIREMENT_ALIGNMENT: {args['requirement_alignment']} | RATIONALE: {args['rationale']}"
    )
    storage.log_event(AGENT_NAME, "innovation_verdict", description)
    return {
        "content": [
            {"type": "text", "text": f"Recorded {verdict} verdict for: {args['innovation'][:70]}"}
        ]
    }


log_event_tool = agent_tools.make_log_event_tool(AGENT_NAME)

ALLOWED_TOOLS = [
    "mcp__storage__calculate",
    "mcp__storage__search_kb",
    "mcp__storage__list_baselines",
    "mcp__storage__get_baseline",
    "mcp__storage__list_requirements",
    "mcp__storage__record_innovation_verdict",
    "mcp__storage__log_event",
]

storage_server = create_sdk_mcp_server(
    name="storage",
    tools=[
        agent_tools.calculate_tool,
        agent_tools.search_kb_tool,
        list_baselines_tool,
        get_baseline_tool,
        list_requirements_tool,
        record_innovation_verdict_tool,
        log_event_tool,
    ],
)

# There is no live dynamic Innovation field agent yet (none of CLAUDE.md's
# dynamic field agents are built), so the default run validates a real,
# already-computed finding inside an existing baseline rather than a
# fabricated idea. Once a real field agent exists, its proposal should be
# passed via --innovation instead of relying on this fallback.
SELF_TEST_INNOVATION = (
    "Increase rotor diameter toward the larger end of baseline 89's own "
    "hover_power_bracket comparison (up to 0.55 m per rotor, 4 rotors) to "
    "reduce hover electrical power and ease the mission energy budget's "
    "hover-dominance problem, versus the 0.40 m case baseline 89 currently "
    "uses for its headline numbers."
)


def build_prompt(innovation: str) -> str:
    return f"""You are the Innovation Validator for a multi-agent electric aircraft
project. Your job per the project constitution: run a fast feasibility check
on ONE candidate innovation, validating it against real Knowledge Base
evidence, a real Math & Physics check (via calculate — never arithmetic in
your own reasoning), and real formal requirements. You do not invent whether
something is proven; you check it.

ABSOLUTE RULE — NEVER DO ARITHMETIC YOURSELF:
Every number you cite must come from a calculate call. If you want to compare
hover power at two rotor sizes, call calculate twice (once per size) and
compare the real results — do not estimate or recall a number from having
seen it in a baseline's text.

{engineering_math.format_formula_docs()}

THE CANDIDATE INNOVATION TO VALIDATE:

"{innovation}"

Steps:
1. list_baselines, then get_baseline on the most recent one with a real
   hover_power_bracket section (baseline 89) to see the real MTOW, disk
   loading assumptions, and the three rotor-size cases already computed
   there.
2. Do NOT trust the baseline's own text numbers as your proof — independently
   re-derive them. Call calculate("disk_area_from_rotors", ...) and
   calculate("hover_power", ...) for the 0.40 m case AND the 0.55 m case
   yourself, using the same MTOW/disk-loading assumptions the baseline
   states, and confirm the real percentage reduction in hover power.
3. search_kb for real evidence on disk loading / rotor size trade-offs to
   ground the math_check in cited evidence, not just the arithmetic alone.
4. list_requirements (baseline_id=0 for all) and check whether any real,
   approved requirement constrains rotor diameter, disk area, or hover time.
   If none do, say so plainly — "no requirement conflicts" is a real,
   honest finding, not a gap to paper over.
5. Call record_innovation_verdict exactly once with your verdict. Use PROVEN
   only if the calculate() comparison shows a genuine, non-trivial reduction
   AND you have real cited KB evidence AND you've checked requirement
   alignment. If the airframe/mechanical cost of larger rotors (fold-out
   arms, prop-wing interaction, tiltrotor mechanical complexity — flagged in
   baseline 89's own "finding" field) means this needs Airframe Engineer's
   real input before it can be called proven, say so and use
   NEEDS_MORE_RESEARCH — that is a legitimate, honest verdict, not a
   non-answer.
6. Finish with ONE log_event, event_type="validation_complete", summarizing
   your verdict and the real numbers behind it.
"""


async def main():
    parser = argparse.ArgumentParser(
        description="Innovation Validator — feasibility check on one candidate innovation"
    )
    parser.add_argument(
        "--innovation",
        help="A real candidate innovation to validate. Omit to run the self-test "
        "(re-derives baseline 89's own rotor-size hover-power finding independently).",
    )
    args = parser.parse_args()

    innovation = args.innovation or SELF_TEST_INNOVATION
    prompt = build_prompt(innovation)
    if args.innovation:
        print(f"===== INNOVATION: {args.innovation} =====\n")

    options = agent_runtime.build_options(
        system_prompt=prompt,
        storage_server=storage_server,
        allowed_tools=ALLOWED_TOOLS,
        max_turns=40,
    )
    stats = await agent_runtime.run_agent(AGENT_NAME, options, prompt)
    print(f"\n===== DONE — cost ${stats['cost']:.4f} =====")


if __name__ == "__main__":
    anyio.run(main)
