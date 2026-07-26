# electric-aircraft-agents

Multi-agent AI system building the research/engineering base for a 1:8-scale
autonomous electric aircraft. See [CLAUDE.md](./CLAUDE.md) for the full
project constitution (mission, constraints, agent roster, rules) — read that
first.

## Repo layout

`main` holds only shared infrastructure. Each agent lives on its own branch:

| Branch | Agent | What it does |
|---|---|---|
| `main` | — | `storage.py` (D1 + Vectorize + R2 wrapper), shared config |
| `agent/test-agent` | Smoke-test agent | Proves storage.py works end to end via a real agent conversation |
| `agent/foundational-research-agent` | Foundational Research Agent | Real WebSearch → extracts specific cited facts → writes to the KB |
| `agent/kb-manager-agent` | KB Manager | Reconciles the KB: flags near-duplicate/overlapping entries, validates citations |
| `agent/orchestrator-agent` | Orchestrator | Decomposes directives, batches decision requests/digests, enforces the escalation rule |

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

Each agent branch has its own script, run directly:

```bash
git checkout agent/foundational-research-agent
python3 foundational_research_agent.py --topic "structural materials"
# or: python3 foundational_research_agent.py --all   (all 6 CLAUDE.md topics)

git checkout agent/kb-manager-agent
python3 kb_manager_agent.py

git checkout agent/orchestrator-agent
python3 orchestrator_agent.py
```

Every agent script prints real-time tool calls/results as it runs, and a
final `cost=$X.XX` line — these hit real Cloudflare + Anthropic APIs, not
mocks, so every run has a real (small) dollar cost.

### What to expect per agent

Based on actual runs, not estimates:

| Agent | Typical cost | Typical turns | What it produces |
|---|---|---|---|
| `test_agent.py` | ~$0.15 | ~10 | Confirms storage.py's core functions (baselines, sign-offs, KB) work when driven by a real agent |
| `foundational_research_agent.py` | $0.75–$1.50 per topic (scales with topic breadth) | 19–31 | 10–20 cited KB entries per topic, each a specific fact with a real source URL |
| `kb_manager_agent.py` | ~$0.15–$0.21 | 2–6 | A reconciliation report: candidate duplicate/overlap pairs classified, citation pass/fail counts |
| `orchestrator_agent.py` | ~$0.12 | 6 | A directive decomposition, a batched decision request, a real milestone digest, and (if triggered) an immediate escalation |

Every run is also traceable in `audit_log` via `agent_start`/`agent_end`
events tagged with a `run_id` (see `storage.log_run_start`/`log_run_end`).

## Adding a new agent

1. `git checkout main && git pull`
2. If it needs a new `storage.py` capability, add it there first, commit to
   `main`, push.
3. `git checkout -b agent/<name>`
4. Write the agent script. Copy the `ClaudeAgentOptions` pattern from an
   existing agent — critically, always set `tools=[]` (or an explicit
   minimal list) and `strict_mcp_config=True`. See the note in CLAUDE.md's
   Git workflow section for why.
5. Test it against real data (not fabricated placeholders), verify results
   independently by querying `storage.py` directly rather than trusting the
   agent's own self-reported summary.
6. Commit, push, `git checkout main` to leave the tree clean for next time.

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
