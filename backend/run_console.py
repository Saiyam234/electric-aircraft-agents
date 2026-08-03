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

_lock = threading.Lock()
_jobs: dict[str, dict] = {}
MAX_JOB_HISTORY = 30


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


def start_job(agent: str, user_input: str | None) -> dict:
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
    # mode == "none": no args, ignores user_input if any was sent

    job_id = str(uuid.uuid4())
    with _lock:
        _jobs[job_id] = {
            "id": job_id,
            "agent": agent,
            "module": spec["module"],
            "mode": spec["mode"],
            "input": user_input,
            "status": "running",
            "output": [],
            "started_at": time.time(),
            "finished_at": None,
            "exit_code": None,
            "pid": None,
        }
        # Bound memory: drop the oldest finished jobs once history grows large.
        if len(_jobs) > MAX_JOB_HISTORY:
            finished = sorted(
                (j for j in _jobs.values() if j["status"] != "running"),
                key=lambda j: j["started_at"],
            )
            for j in finished[: len(_jobs) - MAX_JOB_HISTORY]:
                del _jobs[j["id"]]

    thread = threading.Thread(target=_run_job, args=(job_id, spec["module"], args), daemon=True)
    thread.start()
    return {"job_id": job_id}


def get_job(job_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return None
        return dict(job, output=list(job["output"]))


def list_jobs() -> list[dict]:
    with _lock:
        rows = sorted(_jobs.values(), key=lambda j: j["started_at"], reverse=True)
        return [
            {k: v for k, v in j.items() if k != "output"} | {"output_lines": len(j["output"])}
            for j in rows
        ]
