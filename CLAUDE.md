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
- Scale: 1:8 — DECIDED 2026-07-29 (D1 event 117, answering decision_request
  event 84). "1:8" is descriptive shorthand for the size class only, NOT a
  derivation from any specific full-scale reference aircraft. The hard
  number is an absolute target wingspan of 1.40 m, chosen directly rather
  than derived from a ratio — Saiyam explicitly rejected anchoring to a real
  aircraft (options A/B/D/E, real eVTOL/CTOL precedents from Foundational
  Research Agent's KB research) because doing so would prejudge details the
  founding principle reserves for the cluster; option C (Vahana) was
  additionally rejected for outright anchoring tiltwing architecture. Modeled
  in Fusion 360 at 1:1 / true dimensions of this scale. No "scale down" step
  in CAD.
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

## FINALIZED TOOLCHAIN — one tool per job

This is the decided stack, not a menu. Every line is a commitment; where a
line says DEFERRED it is deferred on purpose and says who owns the decision.
Grounded in real research into what enterprise aerospace teams actually run,
then filtered to what is defensible at solo-build scale.

Total recurring cost: effectively $0. The only paid item is eCalc (~$5
one-off). Fusion 360 is free on a personal/education licence.

### Agent system (running today)
- Runtime: Claude Code + Claude Agent SDK (Python), local.
- Structured storage / PLM equivalent: Cloudflare D1 — baselines,
  requirements, audit log. This is the project's backbone in the same sense
  Teamcenter or Windchill is at enterprise scale: one source of truth that
  everything else references.
- Semantic search: Cloudflare Vectorize + Workers AI (BGE embeddings).
- File storage: Cloudflare R2 (bucket exists; subscription not yet enabled).
- Version control: Git + GitHub.
- Oversight: dashboard.py (Flask, localhost) — read-mostly, with the two
  interventions CLAUDE.md reserves for Saiyam.

### Geometry and CAD
- CAD: Autodesk Fusion 360. Confirmed appropriate for startup/UAV scale;
  CATIA and NX are the real industry standard but only justified at
  Boeing/Airbus contractor scale.
- Whole-aircraft parametric geometry: OpenVSP (free, NASA) — for
  configuration-level layout that Fusion 360 is clumsy at.

### Aerodynamics
- Airfoil and wing analysis: XFLR5 (free).
- Rotor and propeller analysis: XROTOR (free, MIT/Drela). CHOSEN over
  JBLADE and QPROP despite one published comparison rating JBLADE best
  overall, because XROTOR shares the XFOIL lineage that XFLR5 already sits
  on — one airfoil-data ecosystem instead of two. If XROTOR's interface
  proves impractical, JBLADE is the fallback, not a parallel tool.
- CFD, only when the simpler tools genuinely cannot answer it: SimScale
  (free tier). Specifically for hover-to-cruise transition aerodynamics.

### Structures
- First-pass FEA: Fusion 360 Simulation workspace (already owned).
- Composite laminate FEA: CalculiX + PrePoMax (free). The escalation path
  when laminate-level fidelity is needed, which the Airframe Engineer's spar
  and layup work will reach.

### Sizing and optimization
- OpenMDAO + Aviary (free, NASA, pip-installable). Aviary carries the
  GASP/FLOPS sizing equations and targets college senior-design use.

### Propulsion sizing
- eCalc (~$5) for motor/prop/battery matching, plus APC's free published
  propeller performance data.

### Flight control and autonomy
- Platform (ArduPilot vs PX4 vs custom): DEFERRED — Software Engineer
  agent's decision, confirmed explicitly by Saiyam. Not finalized here.
- Simulation: JSBSim flight dynamics driving the chosen platform's SITL,
  with FlightGear or Gazebo for visualisation. Free.
- Ground control station: follows from the platform decision (Mission
  Planner for ArduPilot, QGroundControl for either).

### Electronics and manufacturing
- PCB, only if a custom board becomes necessary: KiCad (free).
- CAM: Fusion 360's built-in CAM.
- Slicer: PrusaSlicer or Cura, determined by whichever printer is used.

### Documentation
- Pandoc (Markdown to PDF) for the Literature Agent's research papers and
  engineering documents.

### Deliberately NOT used — recorded so these stop being re-proposed
- CATIA, Siemens NX, Creo: correct at large-airframe scale, not here.
- ANSYS, MSC Nastran/Patran: enterprise-licensed; SimScale and CalculiX
  cover our real fidelity needs.
- Teamcenter, Windchill, 3DEXPERIENCE/ENOVIA: enterprise PLM. D1 plus the
  audit log already provides the part of this that matters at our scale
  (traceable state, versioned baselines).
- IBM DOORS Next, Jama Connect, Polarion: enterprise requirements tools.
  The D1 requirements table plus Systems Engineer covers the same need.
- Cameo Systems Modeler, IBM Rhapsody: enterprise MBSE. If formal system
  modelling is ever genuinely needed, Capella (free, open source, Thales) is
  the pick — but nothing currently requires it.
- Systems Tool Kit (STK): orbital mechanics. Irrelevant to an atmospheric
  eVTOL; listed only because it appears on generic aerospace-software lists.
- MATLAB/Simulink: DEFERRED rather than rejected — genuinely the industry
  standard for flight-control development, and tied to the still-open
  flight-control platform decision above.

### Known gaps in this stack versus enterprise practice
Recorded honestly rather than papered over:
1. Change-impact propagation. When a requirement changes, nothing currently
   tells you what breaks. This is enterprise PLM's core job and the largest
   real gap; it is also cheap to close at our scale.
2. Configuration control. Baselines exist, but with no locked as-designed
   configuration and no formal change-approval path.
3. Verification traceability (requirement -> test -> result). Blocked on the
   V&V and Assurance Gate agents, none of which are built.
4. Interface definitions. CLAUDE.md assigns these to the Systems Engineer;
   that part of its role is unbuilt.

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
5. THEN orchestration/handoff logic between agents — DONE, for real, twice
   over. Orchestrator decomposed the "resolve the 1:8 scale basis" directive
   into a queued `decision_request` (event 84) fed by Foundational Research
   Agent's real reference-aircraft research (event 74, 17 KB entries), and
   separately drove the full Wave 1 -> Wave 2 sequence: requirements ->
   configuration (baseline 89) -> Airframe/Propulsion review -> Chief
   Integration adjudication, with agents reading each other's real output
   from D1, not fabricated handoffs.
6. Fake-data dry-run — SKIPPED, deliberately. Real runs (Wave 1 and Wave 2)
   turned out cheap and fast enough that rehearsing with fake data added
   nothing; every step so far has real Cloudflare-backed output instead.

## Agent build waves — how the remaining roster gets built
The 19 fixed agents are NOT built all at once. Most of them have nothing real
to work on until earlier ones produce output — Manufacturing Manager needs a
design to cost out, the Assurance Gate needs a real baseline to sign off,
Physical Testing needs an aircraft. Building them early produces unverifiable
scaffolding, which breaks the rule that every agent is verified against real
data before being trusted.

- BUILT: Orchestrator, Foundational Research Agent, KB Manager (all verified
  against real data).
- WAVE 1 — BUILT AND RUN FOR REAL. Systems Engineer, Configuration Synthesis
  Lead, Math & Physics Engine ran the full requirements -> configuration ->
  numerical validation loop against real KB/D1 data. Produced baseline 88
  (v0.1-config-draft, 1.40 m span, MTOW 2.5 kg) and then baseline 89
  (`v0.1-config-draft-1785188637`, architecture-agnostic sizing envelope,
  1.25 m span / 0.231 m² wing / MTOW 2.5 kg / wing loading 10.8 kg/m²),
  plus requirements #21-32. Baseline 89 deliberately left VTOL architecture
  and the 1:8 scale reference unresolved (see "Still open" below) rather
  than defaulting either.
- WAVE 2 — BUILT AND RUN FOR REAL, except Innovation Validator (still
  unbuilt). Airframe Engineer, Propulsion & Power Engineer, and Chief
  Integration Agent all ran against baseline 89:
  - Airframe Engineer locked airfoil (SD7003, CL_max 1.0), recomputed
    CD0/V_stall, and filed a structural objection: the spar check's 600 MPa
    allowable had no hand-layup knockdown factor at n=3.8 (event 91).
  - Propulsion & Power Engineer found and fixed a real bug: hover electrical
    power had been computed via `electrical_power_required()`, which applies
    a `propeller_efficiency` term that is undefined in hover (thrust x
    velocity / power, and velocity=0 at hover) and already double-counted by
    figure_of_merit. This inflated hover power to 306.4 W instead of the
    correct ~187 W and wrongly implied the mission energy budget didn't
    close. Root-caused, hand-verified independently (not taken on the
    agent's word), and fixed structurally by adding
    `hover_electrical_power()` to engineering_math.py with no
    `propeller_efficiency` parameter, so the mistake can't recur by
    construction. With the fix: the energy loop CLOSES at MTOW 2.5 kg with
    4x0.40 m rotors, no mass spiral (event 96/99).
  - Chief Integration Agent read both proposals from shared D1 state
    (`get_proposals` tool) in a single prompt and adjudicated: 7 ACCEPT, 2
    MODIFY, 0 REJECT. See "Still open" / Part 3 note below on how this
    adjudication actually happened.
  - Innovation Validator — BUILT AND RUN FOR REAL 2026-07-31, closing out
    Wave 2. Real self-test (no dynamic Innovation field agents exist yet, so
    it validated a real finding already sitting inside baseline 89's own
    hover_power_bracket rather than a fabricated candidate): independently
    re-derived hover power at 4x0.40m vs 4x0.55m rotors via calculate()
    (193.5W -> 140.7W electrical, ~27% reduction; mission hover-energy share
    35% -> 19.9%), cross-checked real KB evidence (Grokipedia, Krossblade,
    MDPI Aerospace) and all approved requirements (21-32, 42) for conflicts
    (found none). Verdict: NEEDS_MORE_RESEARCH, not PROVEN — correctly
    recognized the energy case is closed but the airframe-integration cost
    (arm span vs. wingspan, prop-wing download, tilt-mechanism sizing) is
    Airframe Engineer's call, not its own. Real structural validation: PROVEN
    verdicts are rejected by the tool itself unless kb_evidence AND
    math_check are both non-empty.
- WAVE 3 — BUILT AND RUN FOR REAL 2026-07-31. Software Engineer, Design
  Realization Agent, and Simulation Agent all ran against baseline 89:
  - Simulation Agent independently re-derived the Concurrent Engineering
    Cluster's own Wave 2 adjudicated corrections from scratch via
    calculate() — not trusted from either baseline 89's stale stored config
    (which still shows the pre-review CL_max=1.1/V_stall=12.55) or from
    Airframe Engineer's review text. All three CONFIRMED: V_stall 13.163 m/s
    (vs. claimed 13.16), root bending moment 13.006 N*m (vs. 13.01), spar
    stress 46.45 MPa / safety factor 8.61 (vs. ~46.45 / ~8.6). This run
    surfaced a real bug in engineering_math.calculate(): its rounding used a
    fixed `round(x, 6)`, which silently zeroed out the real 1.96e-9 m^4
    second-moment-of-area result (legitimately tiny in SI units). The model
    then used the correct value in its next call anyway — i.e. it did the
    arithmetic itself and got lucky, the exact failure mode this module
    exists to prevent. Fixed structurally: `calculate()` now rounds to 6
    significant figures, not 6 decimal places, with a regression test
    (`test_calculate_does_not_zero_out_small_si_results`) asserting a small
    real result is never silently zeroed. Full suite: 43/43 passing.
    Software verification (unit-testing flight-controller code) explicitly
    NOT attempted — no such code or spec exists yet; logged as such rather
    than faked.
  - Software Engineer proposed the architecture-agnostic half of the flight
    stack: EKF-based state estimation (ArduPilot/PX4-class), cruise
    waypoint control (L1 + TECS, tied to baseline 89's real 18 m/s cruise
    and 12.55 m/s stall), a concrete EMI mitigation plan for requirement 31
    (antenna separation, phase-wire routing, ferrites, EKF innovation
    gating, a mandatory pre-hover motors-spinning EMI test), and GPS/IMU/
    telemetry-loss failsafes for requirement 30 (GPS-loss dead-reckon at a
    real calculate()-derived best-glide speed of 15.58 m/s). Correctly
    refused to design hover-phase or transition control, since VTOL
    architecture is still unselected. Raised a real objection: requirement
    30 cannot be fully closed at this baseline and should be split into a
    closable cruise-phase half and an architecture-blocked hover/transition
    half.
  - Design Realization Agent generated a real, syntactically valid Fusion
    360 Python API script (`fusion_scripts/wing_planform.py`, verified with
    `ast.parse`) for the wing planform only, using baseline 89's real
    stored dimensions (span 1.25 m, root/tip chord, MAC, AR). Did NOT
    silently rescale to the decided 1.40 m target itself (that is
    Configuration Synthesis Lead's job, not its own) — the script's header
    carries an unmissable flag that the span is stale and the script must
    be regenerated once baseline 89 is corrected. Full-aircraft geometry is
    explicitly out of scope pending VTOL architecture selection.
  - Real cost across all four Wave 3 runs (including Innovation Validator):
    $2.0136, 47 turns total, 0 errors, 0 turn-limit hits.
- WAVE 4 (needs a complete design/baseline): Review & Critic, Safety & Risk,
  Regulatory, Manufacturing Manager, Literature Agent, Physical Testing Agent.
  Not started — most genuinely need a converged spec (VTOL architecture
  selected, baseline re-derived to 1.40 m) that does not exist yet, unlike
  Wave 3 which had real partial data to work against.

Cluster messaging: CLAUDE.md's stated trigger for building it ("genuinely
competing voices to arbitrate") has now technically been met — Wave 2 produced
a real disagreement (Airframe's structural objection vs. Propulsion & Power's
proposal). Confirmed directly: this was NOT live back-and-forth between
running agent instances. It was one script invoking three separate CLI
processes sequentially, with Chief Integration reading both prior agents'
proposals out of shared D1 state (`get_proposals`) into a single prompt.
That's sequential-script-plus-shared-state, not messaging. Recorded here as a
deliberate decision, not something that slid past: real cluster messaging
(agents exchanging messages mid-run, multi-round, with an escalation path
after 3 unresolved rounds) is still NOT built. Whether to build it now is
still open — not decided by this note.

## Explicitly deferred (revisit later, don't rebuild from scratch)
- Agent-sprawl pruning policy for retired dynamic agents
- Data Analyst role (add only once several real baselines exist to analyze)
- Full directives/reports audit folder structure beyond the event_log table
- AWS hosting (AgentCore Runtime) and AWS storage — explicit future
  milestone, not a decision to make right now

## Still open — do not assume resolved
- Baseline 89 needs revision now that the 1:8 basis is decided (see "Scale:
  1:8" above). Baseline 89's wingspan (1.25 m) was derived from a "notional
  ~10 m GA-class reference... NOT a commitment" placeholder; the decided
  target is 1.40 m (a ~12% increase), which propagates: wing area, aspect
  ratio, wing loading, stall speed, Reynolds number, cruise power, the hover
  power bracket, and mission energy all derive from span in baseline 89's
  config. NOT yet re-derived — this needs a real Configuration Synthesis
  Lead + Math & Physics Engine run against the new 1.40 m target (a new
  agent spend), not a hand-patch of baseline 89's numbers, to keep the
  no-arithmetic-by-hand discipline. Flagged, not started.
- Real cluster messaging (agents exchanging messages mid-run, multi-round,
  auto-escalation after 3 unresolved rounds) — NOT built. Its stated trigger
  ("genuinely competing voices to arbitrate") was met in Wave 2 (Airframe's
  structural objection vs. Propulsion & Power's proposal), but Chief
  Integration resolved it via sequential script + shared D1 state read into
  one prompt, not live messaging. Whether to build real messaging now is an
  open decision, not yet made either way.
- Human override / kill-switch capability
- R2 subscription — bucket exists, but not unlocked (needs a card on file);
  not currently blocking anything since R2 isn't needed yet
- AWS billing alert — not urgent since AWS isn't being used right now;
  required again only once AWS hosting is actually revisited
