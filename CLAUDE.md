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
- Takeoff/landing: DECIDED — eVTOL (vertical takeoff and landing). This is a
  capability requirement, the same tier as propulsion and flight autonomy
  level — it is NOT a specific engineering solution and does not decide the
  VTOL architecture. Which configuration (tiltrotor, tiltwing, lift+cruise
  hybrid with separate hover/cruise propulsion, tailsitter, etc.) is
  explicitly NOT Saiyam's to choose, per the founding principle — it is
  discovered, proven, and selected by the Concurrent Engineering Cluster
  like any other engineering solution, never defaulted toward a reference
  design just because it's familiar. (Context: this requirement was added
  after Saiyam saw a tiltrotor eVTOL project online — the architecture is
  explicitly left open specifically so that inspiration doesn't become the
  answer by default.)
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

## Aircraft engineering toolchain
Distinct from the "Tech stack" above, which is about the AGENT infrastructure
(where agents run, where they store data). This section is about the
software used to actually design/analyze/build the AIRCRAFT. Same
founding-principle split applies: infrastructure/tooling is decided
directly (like Cloudflare above); anything that touches the actual
engineering approach is reserved for the agent system, confirmed explicitly
by Saiyam even for a case (flight-control software platform) that could
have plausibly been argued either way.

Grounded in real research (WebSearch, cited) into what actual eVTOL/UAV
engineering teams use — not assumptions.

DECIDED (infrastructure/tooling — analyzes or supports whatever the agents
design, doesn't dictate an engineering answer):
- CAD: Fusion 360. Confirmed realistic for startup/hobbyist eVTOL scale;
  CATIA/NX are the real industry gold standard but only become necessary at
  Boeing/Airbus contractor scale.
- Aerodynamics analysis: XFLR5 (free, airfoil/wing-level) + OpenVSP (free,
  NASA, parametric whole-aircraft geometry) — complementary, not
  overlapping.
- CFD, as-needed (not day-one): SimScale (free tier) — confirmed used
  specifically for VTOL hover-to-cruise transition aerodynamics, which is
  exactly our open problem once a VTOL architecture is chosen.
- Structural analysis: Fusion 360's built-in Simulation workspace. No new
  tool needed; heavier tools (Ansys/Simcenter) are enterprise-priced and
  not justified at this scale.
- Propulsion sizing: eCalc + APC propeller performance data — standard
  RC-community tools for motor/prop/battery matching before buying
  hardware.
- Electronics, if/when a custom board becomes necessary: KiCad (free).
- Manufacturing: Fusion 360 CAM + a slicer (Cura/PrusaSlicer, TBD by
  printer) — fabrication method itself is still open (see below), tool
  choice is ready whenever that's resolved.
- Requirements tracking: the existing D1 `requirements` table (already
  built), not an enterprise tool. Real programs use IBM DOORS/Jama
  Connect/Polarion for this (confirmed via research), but those are
  enterprise-licensed and unjustified for solo scale — our lightweight
  system already covers the core need (traceable requirements linked to a
  baseline).
- Documentation pipeline: Pandoc (Markdown -> PDF), for Literature Agent's
  eventual research-paper/engineering-doc deliverables.
- Design-space optimization: OpenMDAO (NASA, open source, Python) with
  Aviary, NASA's aircraft sizing/optimization tool built on it. Aviary
  carries the sizing equations from GASP and FLOPS and is explicitly used
  by college senior-design courses, NASA internally, and industry — i.e.
  it is aimed at exactly our scale rather than being scaled-down enterprise
  software. It is also a natural fit for this project specifically: it
  decomposes a design problem into disciplinary components that each own
  their own computation, which is structurally the same shape as the
  Concurrent Engineering Cluster.
- Propeller/rotor analysis: XROTOR (MIT, Drela) and JBLADE. This closes a
  real gap — the project's single largest open number is hover power, which
  is set by rotor performance, and momentum theory alone (what
  engineering_math currently provides) gives an ideal-power floor rather
  than a real rotor's performance. These are blade-element-momentum codes
  that use actual airfoil polars. Published comparison found JBLADE gave
  the best overall results against JavaProp and QPROP.
- Flight dynamics simulation: JSBSim (flight dynamics model) driving
  ArduPilot SITL, with FlightGear or Gazebo for visualisation. This is the
  standard open-source stack and matters for the autonomy constraint —
  transition control is the hardest part of a VTOL and must be exercised in
  simulation long before any airframe exists.
- Structural FEA: CalculiX (open source, Abaqus-input-compatible), with
  PrePoMax as a GUI. Supports composite laminate modelling, which the
  Airframe Engineer's spar and layup work actually needs. Fusion 360's
  built-in Simulation stays the first-pass tool; CalculiX is the escalation
  path when laminate-level fidelity is required.

EVALUATED AND DELIBERATELY NOT ADOPTED (recorded so they don't get
re-proposed as gaps):
- CATIA, Siemens NX: the genuine industry standard for large aircraft, and
  the right answer at Boeing/Airbus contractor scale. Not here — enterprise
  licensing for capability this project cannot use.
- ANSYS Fluent/Mechanical, MSC Nastran/Patran: same reasoning. SimScale's
  free tier and CalculiX cover our actual fidelity needs.
- Systems Tool Kit (STK): orbital mechanics and satellite mission analysis.
  Not applicable — this is an atmospheric fixed-wing eVTOL, not a
  spacecraft. Listed only because it appears on generic "aerospace
  software" lists and would otherwise look like an oversight.
- MATLAB/Simulink: genuinely the industry standard for flight-control
  development, and a student licence is affordable. Deferred rather than
  rejected — it belongs to the Software Engineer agent's still-open
  flight-control platform decision (see below), not to this list.

EXPLICITLY DEFERRED to the relevant future agent (not decided here, recorded
so this isn't silently forgotten):
- Flight-control software platform (ArduPilot vs. PX4 vs. custom) —
  Software Engineer agent's call once it exists, via the same "propose with
  impact assessment" pattern Systems Engineer already uses. Confirmed
  explicitly with Saiyam: even though this is more "development platform"
  than "physical design," it stays agent-territory rather than being
  finalized directly.
- Ground control station software — follows from the above.
- SITL/HIL simulation & flight-control V&V approach — Simulation Agent's
  call once it exists.
- Specific VTOL architecture — already established as Concurrent
  Engineering Cluster territory (see eVTOL hard constraint above).

## Git workflow
- Everything lives on `main`. Shared infrastructure (`storage.py`,
  `config.py`, `agent_runtime.py`, `requirements.txt`, this file) sits at the
  repo root; every agent script lives in `agents/`.
- HISTORICAL NOTE: agents used to live one-per-branch (`agent/<name>`). That
  was abandoned once the merge cost became clear — every shared change had to
  be merged into every agent branch (~24 merges at just four agents), and a
  shared fix like the MCP security one below would have needed applying 19
  separate times. Those branches were merged into `main` and deleted.
- `agents/` is a Python package (`__init__.py`), so agents run as
  `python3 -m agents.<name>` from the repo root. Running
  `python3 agents/<name>.py` directly puts `agents/` on `sys.path` instead of
  the repo root and breaks every agent's `import storage`.
- `.env` (real credentials) is gitignored and never committed. `.env.example`
  has the non-secret resource identifiers filled in as a template; the actual
  API token field is always left blank there.
- Every agent MUST build its options via `agent_runtime.build_options()`,
  which forces `tools` (defaulting to none) and `strict_mcp_config=True`.
  Without both, a spawned agent process inherits the full user-level MCP
  server config (e.g. Gmail, Calendar, Drive) regardless of `allowed_tools`,
  which only pre-approves specific tools without restricting what's visible.
  This is not hypothetical — it happened during the KB Manager build and
  exposed exactly that. Constructing `ClaudeAgentOptions` by hand in a new
  agent re-opens the hole; go through `build_options()` so it can't happen.

## Build order (don't skip steps)
1. Storage layer (storage.py) — DONE. Tested against real D1/Vectorize/R2.
2. One working agent, tested locally twice — DONE (`test_agent.py`).
3. Foundational Research Agent (Knowledge Base) — DONE, with real WebSearch
   access. Two topics researched so far with real, cited sources.
4. 2-3 more individual agents, each tested alone — DONE: KB Manager and
   Orchestrator, both tested against real (not fabricated) project data.
5. THEN orchestration/handoff logic between agents — CURRENT STEP, IN
   PROGRESS. A real handoff test (Orchestrator decomposes a directive into
   a specific question -> that exact question passed to Foundational
   Research Agent -> result verified landed in the KB) has been attempted
   and paused twice (once interrupted mid-setup, once explicitly deferred
   by Saiyam pending agent hardening) — not yet actually completed.
6. THEN a hand-run dry-run of the full lifecycle with fake data. May be
   worth revisiting once step 5 lands and KB coverage broadens — real runs
   have proven cheap and fast enough that a fake-data rehearsal may add
   less than just doing a real one with 1-2 more agents.

## Agent build waves — how the remaining roster gets built
The 19 fixed agents are NOT built all at once. Most of them have nothing real
to work on until earlier ones produce output — Manufacturing Manager needs a
design to cost out, the Assurance Gate needs a real baseline to sign off,
Physical Testing needs an aircraft. Building them early produces unverifiable
scaffolding, which breaks the rule that every agent is verified against real
data before being trusted.

- BUILT: Orchestrator, Foundational Research Agent, KB Manager (all verified
  against real data).
- WAVE 1 — BUILT, NOT YET RUN: Systems Engineer, Configuration Synthesis
  Lead, Math & Physics Engine. These work on data that already exists (KB
  entries, requirements table, hard constraints) and form a real loop:
  requirements -> configuration -> numerical validation.
- WAVE 2 (needs a real configuration to exist first): Airframe Engineer,
  Propulsion & Power Engineer, Chief Integration Agent, Innovation Validator.
- WAVE 3 (needs a converged spec): Software Engineer, Design Realization
  Agent, Simulation Agent.
- WAVE 4 (needs a complete design/baseline): Review & Critic, Safety & Risk,
  Regulatory, Manufacturing Manager, Literature Agent, Physical Testing Agent.

Cluster messaging is deliberately unbuilt. CLAUDE.md describes the Concurrent
Engineering Cluster as "one continuously-messaging team," which the current
one-script-one-conversation pattern doesn't provide. Wave 1's three agents run
sequentially and don't need it; building a multi-round cluster driver now
would mean designing against imagined requirements. Revisit at Wave 2, when
there are genuinely competing voices to arbitrate.

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
