# Project Constitution — read this before doing anything in this repo

## What this project is
A multi-agent AI system that autonomously researches, innovates, and engineers
a 1:8-scale electric aircraft with autonomous (self-flying) capability.
Fusion 360 model + engineering/research docs this year; IRL build decided
later; multi-year program spanning high school.

## Founding principle — never violate this
The human owner (Saiyam) defines the problem. The agent ecosystem discovers
the solution.
- Saiyam owns: mission, hard constraints, success criteria, priority changes.
- Saiyam does NOT own: wing configuration, tail type, motor/battery placement,
  structural approach, or any specific engineering solution. These are
  discovered, proven, and selected by the agents — never authored by Saiyam,
  never defaulted toward a reference aircraft just because it's familiar.

## Current hard constraints
- Scale: 1:8 — the real, true target size of the aircraft. Modeled in Fusion
  360 at 1:1 / true dimensions of this scale. No "scale down" step in CAD.
- Propulsion: electric
- Flight autonomy level: DECIDED — the aircraft flies itself, autonomously,
  with no remote pilot. Current build target: autonomous flight-control-only
  (follows a pre-set flight plan/waypoints on its own, like a standard
  autopilot). Full mission-level autonomy (open-ended decision-making) is the
  explicit LONG-TERM DIRECTION this project is building toward, once the
  flight-control layer is proven reliable — not ruled out, just a later
  step, built on top of a working foundation rather than attempted first.
- Human override / kill-switch capability: STILL OPEN — not yet decided.
- Current deliverable: Fusion 360 model + engineering docs + research papers
- Fabrication: solo build, resources still undetermined
- Fusion 360 integration: manual script handoff. The Design Realization
  agent writes Fusion 360 Python API scripts; Saiyam opens Fusion 360 and
  runs them himself. A live cloud connector exists (Autodesk's Automation
  API for Fusion) but requires a separate developer account, OAuth setup,
  TypeScript instead of Python, and ongoing per-hour cost — not worth it
  for removing one click at this project's scale.

## Human oversight autonomy tier (NOT flight autonomy) — medium-loose hybrid
What reaches Saiyam: batched decision requests at real forks, milestone
digests, and ALWAYS (no exceptions): safety issues, regulatory issues,
irreversible-cost issues.
What stays internal: day-to-day division work, intermediate attempts, minor
iteration cycles.
Direct chat: Saiyam can message any agent directly, at any time. Every agent
classifies the message as a "steer" (factored in, still goes through normal
proof/integration) or a "directive-level change" (routed to the Orchestrator
and logged like any formal directive). If unclear which, the agent asks once
before acting. Any real change from a direct chat is logged, attached to the
current baseline.

## Agent roster — 19 fixed agents, plus dynamic agents
Fixed agents perform a defined, ongoing role. Dynamic agents are created as
needed (one per active research topic or innovation field) and close out
once their task is done — their number varies, so they are listed separately
and not counted in the "19."

### 1. Orchestrator — 1 agent
- **Orchestrator** — decomposes Saiyam's directives into open design
  questions, tracks project state (including baseline versioning and
  schedule/budget risk), batches communication into decision requests and
  digests, and enforces the escalation rule (safety/regulatory/irreversible-
  cost issues always surface immediately — a standing hard rule checked
  against everything this agent does, never deprioritized).

### 2. Knowledge Base — 2 fixed agents + dynamic agents
- **Foundational Research Agent** — proactively builds the initial reference
  library BEFORE specific design questions come up: real web search across
  core topics this project needs (aerodynamics fundamentals, electric
  propulsion, battery chemistry and safety, prior electric aircraft designs,
  structural materials, autonomous flight systems), pulling and citing
  actual papers and sources — not synthesizing from the model's own training
  knowledge alone. MUST be built with real web search tool access, or it
  cannot do this job.
- **KB Manager** — spawns dynamic research agents for later, narrower open
  topics, reconciles and deduplicates all findings (foundational and
  dynamic), tags facts for findability, validates facts to citable status,
  versions everything by baseline, and records rejected ideas/lessons-learned.
- **Dynamic topic agents** — one per active, narrow research question that
  comes up during actual design work (after the foundational sweep), working
  in parallel, closing out once that topic is researched.

### 3. Innovation — 1 fixed agent + dynamic agents
- **Innovation Validator** — runs a fast feasibility check with Engineering,
  validates each proposed innovation against Knowledge Base evidence + Math
  & Physics + formal requirements, and packages proven innovations for
  handoff to the Concurrent Engineering Cluster.
- **Dynamic field agents** — one per active field (e.g. battery efficiency,
  aerodynamic efficiency), working in parallel, proving individual
  improvements field by field — never proposing whole-aircraft concepts.

### 4. Concurrent Engineering Cluster — 8 agents
One continuously-messaging team, not a sequential handoff chain. Configuration
Synthesis Lead is the standing tiebreaker on every dispute; unresolved after
3 rounds, it auto-escalates to him. (DECIDED — 3 rounds.)
- **Configuration Synthesis Lead** — owns the overall aircraft configuration:
  dimensions, wing loading, power loading, general arrangement, weight &
  balance. Standing tiebreaker for the cluster.
- **Chief Integration Agent** — accepts, rejects, or modifies each proven
  innovation against the current configuration.
- **Airframe Engineer** — aerodynamics, structures, mechanical systems
  (landing gear, linkages, actuation), and materials selection.
- **Propulsion & Power Engineer** — propulsion (motor selection, mounting,
  drivetrain), electrical power systems (battery pack, wiring, BMS), thermal
  (cooling/airflow).
- **Math & Physics Engine** — aerodynamic, structural, and thermal
  calculations, plus flight mechanics/stability/trajectory math (the
  calculation side of flight controls — Software Engineer owns the
  implementation side).
- **Systems Engineer** — requirements definition and traceability (proposes
  requirement changes with an impact assessment to Saiyam, never
  unilaterally), interface and agent-message-schema ownership, integration
  test planning, and EMI/EMC (electromagnetic interference between motors,
  wireless nav/telemetry links, and GPS on a small airframe).
- **Software Engineer** — flight controller, telemetry, cockpit/UI,
  autonomous navigation/guidance logic, autopilot implementation (the
  executable side of flight controls), and ground control/override station
  software if a human override capability is confirmed.
- **Design Realization Agent** — writes Fusion 360 Python API scripts once
  the cluster's spec is locked to a baseline (manual script handoff, above).

### 5. Manufacturing — 1 agent
- **Manufacturing Manager** — compiles the bill of materials, researches
  sourcing/vendors, drafts the build sequence, tracks running cost. Produces
  drafts only — no purchase or build commitment until full Assurance
  sign-off and Saiyam's explicit approval. Explicitly flags manufacturability
  problems back to the Engineering Cluster when something is impractical to
  fabricate.

### 6. Verification & Validation — 2 agents
- **Simulation Agent** — computational aerodynamic/structural simulation,
  plus software verification (unit-testing the flight controller/autopilot
  code itself — does it handle bad sensor input gracefully, does it fail
  safely).
- **Physical Testing Agent** — test planning, execution, data analysis, and
  sim-vs-real comparison. A mismatch sends the design back into the
  Concurrent Engineering Cluster.

### 7. Assurance Gate — 3 agents (three separate, independent offices)
All three must sign off before a baseline is stamped. Kept deliberately
separate — a real accountability boundary, not extra headcount.
- **Review & Critic** — cross-system consistency and real-world usability
  audit. Also periodically spot-checks direct-chat history against the log.
- **Safety & Risk** — FMEA and hazard analysis, including autonomy-specific
  failure modes (lost GPS/navigation signal, sensor failure, loss of comms/
  telemetry link) and cybersecurity/link security (GPS spoofing, telemetry
  jamming). Escalates straight to Saiyam regardless of autonomy tier. FMEA
  policy: delta-only re-run for minor baselines, full re-run whenever
  structure, propulsion, or battery changes.
- **Regulatory** — compliance review, including autonomous/uncrewed aircraft
  rules (generally stricter than simple remote-control aircraft rules),
  standard model-aircraft codes, and battery-handling rules.

### 8. Literature — 1 agent
- **Literature Agent** — drafts the interim document at every baseline and
  the capstone paper at project completion, handles citation/formatting, and
  self-reviews before feeding the result back into the Knowledge Base.

## Rules that apply across every agent
- Configuration Synthesis Lead is the standing tiebreaker inside the cluster.
  Unresolved after 3 rounds -> auto-escalate to Saiyam.
- A baseline is stamped only when a design fully clears the Assurance Gate.
  Modify-and-reprove cycles happen within one baseline attempt, not as new baselines.
- Every rejection is logged to the lessons-learned layer, so a dead idea is
  never re-proposed, regardless of where it's fixed.
- Manufacturing produces drafts only — purchases/builds require full
  Assurance sign-off AND Saiyam's explicit approval.
- The Systems Engineer's requirements function is a living process — it
  proposes requirement changes (with an impact assessment) to Saiyam for
  approval; it never changes requirements unilaterally.

## Tech stack — right now: local agents, cloud storage on Cloudflare
- Agent runtime: Claude Code, running locally, for now, via the Claude Agent
  SDK (`claude_agent_sdk` Python package) — each agent is a script that wraps
  storage.py's functions as in-process SDK MCP tools and drives them through
  a real agent conversation. AWS Bedrock AgentCore Runtime is the planned
  future home once agents are proven and Saiyam decides to move to
  continuous/hosted operation — not needed yet.
- Structured storage (baselines, requirements, audit log): Cloudflare D1
- Semantic search / embeddings: Cloudflare Vectorize, using Cloudflare
  Workers AI's built-in embedding model (BGE) to generate the embeddings
  Vectorize stores and searches. Kept entirely on Cloudflare — no separate
  embeddings provider or account needed. 10,000 free Workers AI requests
  ("Neurons") per day comfortably covers a solo project's usage.
- File storage (if ever needed): Cloudflare R2 — bucket created, but the R2
  subscription itself isn't enabled yet (requires adding a card on file for
  the free tier); storage.py's R2 functions raise a clear error until then.
- Why Cloudflare over AWS right now: free with no minimum floor under any
  configuration. AWS's equivalent (DynamoDB + S3) is also genuinely free at
  this scale, but Bedrock Knowledge Base's underlying vector store defaults
  to OpenSearch Serverless, which has historically carried a real minimum
  cost of roughly $350-700/month even sitting idle — an easy, expensive trap
  to fall into by accident. Since agents aren't on AWS yet either, there's no
  "everything in one account" benefit to justify that risk right now.
- FUTURE RE-EVALUATION: if agent hosting ever moves to AWS, revisit storage
  choice at that point. If AWS storage is chosen then, explicitly pick S3
  Vectors or the newer scale-to-zero OpenSearch Serverless — never the
  classic/default OpenSearch Serverless configuration.
- Local development: build and test every agent locally first, deploy
  anywhere is a decision for later.

## Git workflow
- `main` holds only shared infrastructure: `storage.py`, `requirements.txt`,
  `.gitignore`, `.env.example`, this file. Never agent-specific code.
- Every agent gets its own branch off `main` (`agent/<name>`), containing
  just that agent's script. Committed and pushed as soon as it's built and
  tested — see README.md for the current roster and how to run each one.
- `.env` (real credentials) is gitignored and never committed. `.env.example`
  has the non-secret resource identifiers filled in as a template; the actual
  API token field is always left blank there.
- Every ClaudeAgentOptions in every agent script MUST set `tools=[]` (or an
  explicit minimal list like `["WebSearch"]`) and `strict_mcp_config=True`.
  Without both, a spawned agent process inherits the full user-level MCP
  server config (e.g. Gmail, Calendar, Drive) regardless of `allowed_tools`,
  which only pre-approves specific tools without restricting what's visible.
  This was discovered and fixed during the KB Manager build — don't
  reintroduce it in new agents.

## Build order (don't skip steps)
1. Storage layer (storage.py) — DONE. Tested against real D1/Vectorize/R2.
2. One working agent, tested locally twice — DONE (`test_agent.py`).
3. Foundational Research Agent (Knowledge Base) — DONE, with real WebSearch
   access. Two topics researched so far with real, cited sources.
4. 2-3 more individual agents, each tested alone — DONE: KB Manager and
   Orchestrator, both tested against real (not fabricated) project data.
5. THEN orchestration/handoff logic between agents — CURRENT STEP.
6. THEN a hand-run dry-run of the full lifecycle with fake data.

## Explicitly deferred (revisit later, don't rebuild from scratch)
- Agent-sprawl pruning policy for retired dynamic agents
- Data Analyst role (add only once several real baselines exist to analyze)
- Full directives/reports audit folder structure beyond the event_log table
- AWS hosting (AgentCore Runtime) and AWS storage — explicit future
  milestone, not a decision to make right now

## Still open — do not assume resolved
- Human override / kill-switch capability
- R2 subscription — bucket exists, but not unlocked (needs a card on file);
  not currently blocking anything since R2 isn't needed yet
- AWS billing alert — not urgent since AWS isn't being used right now;
  required again only once AWS hosting is actually revisited
