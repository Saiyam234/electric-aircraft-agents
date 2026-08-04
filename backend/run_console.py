"""Real agent dispatch for the dashboard's Run Console.

This does not simulate anything: it launches the exact same CLI entrypoint
you'd run by hand (`python3 -m agents.<name> [--directive ...]`), using the
project's real venv interpreter, and streams its real stdout back to the
frontend via polling. Every run through here is a real Claude Agent SDK
call and costs real money — the frontend requires an explicit confirm
before ever hitting the start endpoint, and this module never runs
anything not in RUNNABLE_AGENTS (agent selection is never taken from raw
user input passed to a shell).

This is NOT a chat interface. The underlying agents are one-shot batch
processes, not conversational sessions — an agent runs once against real
current state and produces one real result. Representing this as live
back-and-forth chat would misrepresent what the system actually is.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import uuid

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_PYTHON = os.path.join(REPO_ROOT, ".venv", "bin", "python3")
PYTHON = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable

# mode:
#   "directive" -> passes --directive "<input>"
#   "topic"     -> passes --topic "<input>"
#   "innovation"-> passes --innovation "<input>"
#   "none"      -> no CLI args; runs its fixed real pass against current state
RUNNABLE_AGENTS = {
    "Orchestrator": {"module": "orchestrator_agent", "mode": "directive"},
    "FoundationalResearchAgent": {"module": "foundational_research_agent", "mode": "topic"},
    "KBManager": {"module": "kb_manager_agent", "mode": "none"},
    "InnovationValidator": {"module": "innovation_validator_agent", "mode": "innovation"},
    "SystemsEngineer": {"module": "systems_engineer_agent", "mode": "none"},
    "ConfigurationSynthesisLead": {"module": "configuration_synthesis_lead_agent", "mode": "none"},
    "MathPhysicsEngine": {"module": "math_physics_engine_agent", "mode": "none"},
    "AirframeEngineer": {"module": "airframe_engineer_agent", "mode": "none"},
    "PropulsionPowerEngineer": {"module": "propulsion_power_engineer_agent", "mode": "none"},
    "ChiefIntegrationAgent": {"module": "chief_integration_agent", "mode": "none"},
    "SoftwareEngineer": {"module": "software_engineer_agent", "mode": "none"},
    "DesignRealizationAgent": {"module": "design_realization_agent", "mode": "none"},
    "SimulationAgent": {"module": "simulation_agent", "mode": "none"},
    "ReviewCritic": {"module": "review_critic_agent", "mode": "none"},
    "SafetyRisk": {"module": "safety_risk_agent", "mode": "none"},
    "Regulatory": {"module": "regulatory_agent", "mode": "none"},
    "ManufacturingManager": {"module": "manufacturing_manager_agent", "mode": "none"},
    "PhysicalTestingAgent": {"module": "physical_testing_agent", "mode": "none"},
    "LiteratureAgent": {"module": "literature_agent", "mode": "none"},
}

# The real dependency order this project's own runs have actually used
# (CLAUDE.md's Wave 1-4 structure) — config before validation before
# review before assurance before literature. Orchestrator and Foundational
# Research Agent are excluded: both require a real directive/topic input,
# so they don't fit an unattended sequential run.
PIPELINE_ORDER = [
    "KBManager",
    "SystemsEngineer",
    "ConfigurationSynthesisLead",
    "MathPhysicsEngine",
    "AirframeEngineer",
    "PropulsionPowerEngineer",
    "ChiefIntegrationAgent",
    "InnovationValidator",
    "SoftwareEngineer",
    "DesignRealizationAgent",
    "SimulationAgent",
    "ManufacturingManager",
    "PhysicalTestingAgent",
    "ReviewCritic",
    "SafetyRisk",
    "Regulatory",
    "LiteratureAgent",
]

_lock = threading.Lock()
_jobs: dict[str, dict] = {}
MAX_JOB_HISTORY = 30


def _with_message(args: list[str], message: str | None) -> list[str]:
    if message and message.strip():
        return [*args, "--message", message.strip()]
    return args


def _run_job(job_id: str, module: str, args: list[str]) -> None:
    # -u: unbuffered stdout/stderr. Without it, a piped (non-tty) child fully
    # buffers its output, so nothing streams to the UI until the process
    # exits — verified for real: a live run sat at 0 output lines for 20+
    # seconds despite real progress happening, until this was added.
    cmd = [PYTHON, "-u", "-m", f"agents.{module}", *args]
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )
        with _lock:
            _jobs[job_id]["pid"] = proc.pid
        for line in proc.stdout:
            with _lock:
                _jobs[job_id]["output"].append(line.rstrip("\n"))
        code = proc.wait()
        with _lock:
            _jobs[job_id]["status"] = "done" if code == 0 else "error"
            _jobs[job_id]["exit_code"] = code
            _jobs[job_id]["finished_at"] = time.time()
    except Exception as exc:  # noqa: BLE001 — surface any launch failure to the UI, never crash the server
        with _lock:
            _jobs[job_id]["status"] = "error"
            _jobs[job_id]["output"].append(f"[run_console] failed to launch: {exc}")
            _jobs[job_id]["finished_at"] = time.time()


def start_job(agent: str, user_input: str | None, message: str | None = None) -> dict:
    if agent not in RUNNABLE_AGENTS:
        return {"error": f"'{agent}' is not a runnable agent. Known: {sorted(RUNNABLE_AGENTS)}"}

    spec = RUNNABLE_AGENTS[agent]
    args: list[str] = []
    if spec["mode"] == "directive":
        if not user_input or not user_input.strip():
            return {"error": "This agent requires a directive."}
        args = ["--directive", user_input.strip()]
    elif spec["mode"] == "topic":
        if not user_input or not user_input.strip():
            return {"error": "This agent requires a research topic."}
        args = ["--topic", user_input.strip()]
    elif spec["mode"] == "innovation":
        if not user_input or not user_input.strip():
            return {"error": "This agent requires a candidate innovation to validate."}
        args = ["--innovation", user_input.strip()]
    # mode == "none": no directive/topic/innovation arg, but --message still applies below
    args = _with_message(args, message)

    job_id = str(uuid.uuid4())
    with _lock:
        _jobs[job_id] = {
            "id": job_id,
            "kind": "single",
            "agent": agent,
            "module": spec["module"],
            "mode": spec["mode"],
            "input": user_input,
            "message": message,
            "status": "running",
            "output": [],
            "started_at": time.time(),
            "finished_at": None,
            "exit_code": None,
            "pid": None,
        }
        _evict_old_jobs()

    thread = threading.Thread(target=_run_job, args=(job_id, spec["module"], args), daemon=True)
    thread.start()
    return {"job_id": job_id}


def _evict_old_jobs() -> None:
    """Caller must hold _lock. Bounds memory by dropping the oldest finished
    jobs once history grows large — shared by both single-agent and
    pipeline job creation."""
    if len(_jobs) > MAX_JOB_HISTORY:
        finished = sorted(
            (j for j in _jobs.values() if j["status"] != "running"),
            key=lambda j: j["started_at"],
        )
        for j in finished[: len(_jobs) - MAX_JOB_HISTORY]:
            del _jobs[j["id"]]


def _run_pipeline(job_id: str, agents: list[str]) -> None:
    """Runs each agent's real CLI entrypoint one at a time, in order,
    waiting for each to finish before starting the next — these agents
    read/write shared D1 state, so running them concurrently would race.
    Stops on the first real failure rather than cascading a broken run
    through the rest of the sequence.

    Before each step launches, checks the job's pending_message — set either
    at pipeline start or live via send_pipeline_message while a prior step
    is still running — and attaches it to that step as a real --message,
    then clears it so it isn't reused for a later step by accident."""
    for agent in agents:
        spec = RUNNABLE_AGENTS[agent]
        with _lock:
            step_message = _jobs[job_id].get("pending_message")
            _jobs[job_id]["pending_message"] = None
        step = {
            "agent": agent,
            "module": spec["module"],
            "message": step_message,
            "status": "running",
            "output": [],
            "started_at": time.time(),
            "finished_at": None,
            "exit_code": None,
        }
        with _lock:
            _jobs[job_id]["steps"].append(step)
            step_index = len(_jobs[job_id]["steps"]) - 1
            _jobs[job_id]["current_step"] = step_index

        cmd = [PYTHON, "-u", "-m", f"agents.{spec['module']}", *_with_message([], step_message)]
        env = {**os.environ, "PYTHONUNBUFFERED": "1"}
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=REPO_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
            )
            for line in proc.stdout:
                with _lock:
                    _jobs[job_id]["steps"][step_index]["output"].append(line.rstrip("\n"))
            code = proc.wait()
            with _lock:
                _jobs[job_id]["steps"][step_index]["status"] = "done" if code == 0 else "error"
                _jobs[job_id]["steps"][step_index]["exit_code"] = code
                _jobs[job_id]["steps"][step_index]["finished_at"] = time.time()
            if code != 0:
                with _lock:
                    _jobs[job_id]["status"] = "error"
                    _jobs[job_id]["finished_at"] = time.time()
                return
        except Exception as exc:  # noqa: BLE001 — surface, never crash the server
            with _lock:
                _jobs[job_id]["steps"][step_index]["status"] = "error"
                _jobs[job_id]["steps"][step_index]["output"].append(f"[run_console] failed to launch: {exc}")
                _jobs[job_id]["steps"][step_index]["finished_at"] = time.time()
                _jobs[job_id]["status"] = "error"
                _jobs[job_id]["finished_at"] = time.time()
            return

    with _lock:
        _jobs[job_id]["status"] = "done"
        _jobs[job_id]["finished_at"] = time.time()


def start_pipeline(agents: list[str] | None = None, message: str | None = None) -> dict:
    """Real sequential dispatch of multiple agents in one job. `agents`
    defaults to the full real PIPELINE_ORDER; pass a subset (still in
    PIPELINE_ORDER's relative order) to run only some steps. Every agent
    named must be RUNNABLE_AGENTS with mode='none' or 'innovation' (which
    self-tests with no input) — 'directive'/'topic' agents can't run
    unattended and are rejected here.

    `message`, if given, is attached to the FIRST step only (a real message
    from Saiyam sent before the run started) — to reach a later step, use
    send_pipeline_message once the run is in progress instead of assuming
    every agent wants the same note."""
    selected = list(agents) if agents else list(PIPELINE_ORDER)
    unknown = [a for a in selected if a not in RUNNABLE_AGENTS]
    if unknown:
        return {"error": f"Unknown agent(s): {unknown}"}
    needs_input = [a for a in selected if RUNNABLE_AGENTS[a]["mode"] == "directive" or RUNNABLE_AGENTS[a]["mode"] == "topic"]
    if needs_input:
        return {"error": f"These agents need a real directive/topic and can't run unattended in a pipeline: {needs_input}"}
    if not selected:
        return {"error": "No agents selected."}

    job_id = str(uuid.uuid4())
    with _lock:
        _jobs[job_id] = {
            "id": job_id,
            "kind": "pipeline",
            "agent": "Pipeline",
            "agents": selected,
            "status": "running",
            "steps": [],
            "current_step": -1,
            "pending_message": message,
            "started_at": time.time(),
            "finished_at": None,
        }
        _evict_old_jobs()

    thread = threading.Thread(target=_run_pipeline, args=(job_id, selected), daemon=True)
    thread.start()
    return {"job_id": job_id}


def send_pipeline_message(job_id: str, message: str) -> dict:
    """Attaches a real message to whichever step hasn't launched its
    subprocess yet — the pipeline is a sequence of real one-shot batch runs,
    not a live conversation, so this can't interrupt a step already in
    progress; it queues for the next one, same as CLAUDE.md's direct-chat
    model (a message lands before an agent acts, not mid-thought)."""
    if not message or not message.strip():
        return {"error": "Message is empty."}
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return {"error": "Unknown job_id."}
        if job["kind"] != "pipeline":
            return {"error": "Not a pipeline job."}
        if job["status"] != "running":
            return {"error": "This pipeline has already finished — nothing left to send it to."}
        job["pending_message"] = message.strip()
    return {"ok": True}


def get_job(job_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return None
        if job["kind"] == "pipeline":
            steps = [dict(s, output=list(s["output"])) for s in job["steps"]]
            return dict(job, steps=steps)
        return dict(job, output=list(job["output"]))


def list_jobs() -> list[dict]:
    with _lock:
        rows = sorted(_jobs.values(), key=lambda j: j["started_at"], reverse=True)
        result = []
        for j in rows:
            if j["kind"] == "pipeline":
                summary = {k: v for k, v in j.items() if k != "steps"}
                summary["step_count"] = len(j["steps"])
            else:
                summary = {k: v for k, v in j.items() if k != "output"}
                summary["output_lines"] = len(j["output"])
            result.append(summary)
        return result
