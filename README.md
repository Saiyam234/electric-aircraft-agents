# electric-aircraft-agents

Multi-agent AI system building the research/engineering base for a 1:8-scale
autonomous electric aircraft. See [CLAUDE.md](./CLAUDE.md) for the full
project constitution (mission, constraints, agent roster, rules) — read that
first.

## Repo layout

Everything is on `main`. Shared infrastructure at the repo root, agents in
`agents/`:

| File | What it is |
|---|---|
| `storage.py` | Cloudflare D1 + Vectorize + R2 wrapper — every agent goes through this |
| `agent_runtime.py` | Shared options builder + streaming loop; forces the MCP security settings |
| `config.py` | Constants and validation bounds |
| `verify_setup.py` | Preflight check that credentials work and the DB is initialized |
| `test_storage.py` | Integration test suite for the storage layer |

| Agent (`agents/`) | What it does |
|---|---|
| `test_agent` | Smoke test — proves storage.py works end to end via a real agent conversation |
| `foundational_research_agent` | Real WebSearch → extracts specific cited facts → writes to the KB |
| `kb_manager_agent` | Reconciles the KB: flags near-duplicate/overlapping entries, validates citations |
| `orchestrator_agent` | Decomposes directives, batches decision requests/digests, enforces the escalation rule |
| `systems_engineer_agent` | Derives verifiable requirements from hard constraints + KB evidence (proposes only) |
| `configuration_synthesis_lead_agent` | Drafts the aircraft sizing envelope; deliberately leaves VTOL architecture open |
| `math_physics_engine_agent` | Validates a configuration's numbers — arithmetic runs in Python, not the model |

Agents used to live one-per-branch; that was abandoned once the merge cost
became clear (see CLAUDE.md's Git workflow section).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then fill in your Cloudflare API token and resource IDs
```

The Cloudflare API token needs `D1:Edit`, `Vectorize:Edit`, `Workers AI:Edit`,
`Workers R2 Storage:Edit` permissions on your account.

Agents also need the standalone `claude` CLI logged in (separate from
whatever authenticates your main Claude Code session):

```bash
claude
# then inside: /login
```

## Running an agent

Run as a module from the repo root (not `python3 agents/foo.py` — that breaks
`import storage`, see CLAUDE.md's Git workflow section):

```bash
python3 -m agents.foundational_research_agent --topic "structural materials"
# or --all for the six CLAUDE.md core topics

python3 -m agents.kb_manager_agent
python3 -m agents.orchestrator_agent

# Wave 1 engineering loop, in this order:
python3 -m agents.systems_engineer_agent
python3 -m agents.configuration_synthesis_lead_agent
python3 -m agents.math_physics_engine_agent
```

Every agent script prints real-time tool calls/results as it runs, and a
final `cost=$X.XX` line — these hit real Cloudflare + Anthropic APIs, not
mocks, so every run has a real (small) dollar cost.

### What to expect per agent

Based on actual runs, not estimates:

| Agent | Typical cost | Typical turns | What it produces |
|---|---|---|---|
| `test_agent` | ~$0.15 | ~10 | Confirms storage.py's core functions (baselines, sign-offs, KB) work when driven by a real agent |
| `foundational_research_agent` | $0.75–$1.50 per topic (scales with topic breadth) | 19–31 | 10–20 cited KB entries per topic, each a specific fact with a real source URL |
| `kb_manager_agent` | ~$0.15–$0.40 | 2–6 | A reconciliation report: candidate duplicate/overlap pairs classified, citation pass/fail counts |
| `orchestrator_agent` | ~$0.12–$0.21 | 6 | A directive decomposition, a batched decision request, a real milestone digest, and (if triggered) an immediate escalation |
| `systems_engineer_agent` | not yet measured | — | ~8–14 proposed requirements, each with an impact assessment, all status `proposed` |
| `configuration_synthesis_lead_agent` | not yet measured | — | A draft baseline holding the sizing envelope + VTOL architecture comparison (selection left open) |
| `math_physics_engine_agent` | not yet measured | — | A numerical verdict on whether a configuration closes, every figure from a Python calculation |

The three Wave 1 agents are built but have not been run yet — their costs are
marked "not yet measured" rather than estimated, since every other number in
this table comes from a real observed run.

Every run is also traceable in `audit_log` via `agent_start`/`agent_end`
events tagged with a `run_id` (see `storage.log_run_start`/`log_run_end`).

## Adding a new agent

1. `git pull`
2. If it needs a new `storage.py` capability, add it there first, with a test.
3. Create `agents/<name>_agent.py`. Follow an existing agent's shape:
   `@tool`-decorated wrappers around `storage.py` functions, a
   `create_sdk_mcp_server(name="storage", ...)`, an `ALLOWED_TOOLS` list of
   `mcp__storage__*` entries, and a prompt.
4. Build options with `agent_runtime.build_options(...)` and run with
   `agent_runtime.run_agent(...)`. Do NOT hand-construct `ClaudeAgentOptions`
   — `build_options` is what forces the MCP security settings, and bypassing
   it re-opens a hole that already bit this project once (CLAUDE.md, Git
   workflow section).
5. Conventions worth matching: numeric tool args are typed `float` in the
   schema and cast with `int()` at use; tools never raise (catch and return a
   `[REJECTED]`/`[SKIP]` string, with `"is_error": True` for real rejections);
   anything deterministic is computed in Python rather than asked of the model.
6. Test against real data, and verify results by querying `storage.py`
   directly rather than trusting the agent's self-reported summary.

## Tests

`pytest test_storage.py` runs a regression suite against the storage layer
directly (real D1/Vectorize calls, cleans up its own test data afterward).
This is separate from agent testing above — agents are validated by running
them for real and checking outcomes, not unit tests, since their correctness
is about judgment quality (is this a good research fact? is this really a
duplicate?), not deterministic function behavior.

R2 isn't enabled on the account yet (needs a card on file for the free
tier), so there are no R2-specific tests — `verify_setup.py` checks it
non-blockingly (`[SKIP]`, not `[FAIL]`) and `storage.py`'s R2 functions
raise a clear `R2NotEnabledError` until then.

## Deduplication strategy

**Exact duplicates** (same `entry_id`) are rejected at write time by
`storage.upsert_kb_checked()` — it checks whether the ID already exists
before upserting and raises `ValueError` instead of silently overwriting.
This guards the realistic case: re-running the same research topic, where
the agent naturally regenerates the same descriptive slug for the same
fact. `foundational_research_agent.py` catches that `ValueError`, logs a
`duplicate_detected` audit event, skips the entry, and continues rather
than crashing — the final summary reports both `entries_created` and
`entries_skipped`.

**Near-duplicates** (same underlying fact, different wording or a
different `entry_id`) are *not* caught by the check above — that's KB
Manager's job: cosine similarity between embeddings surfaces candidate
pairs, which get human-reviewed judgment (`TRUE_DUPLICATE` / `OVERLAP` /
`FALSE_POSITIVE`), never auto-merged or auto-deleted. If KB Manager ever
sees near-identical text under different IDs from the *same* topic run,
that indicates a bug in the write-time check above, not just an
expected overlap — its prompt flags that case explicitly.
