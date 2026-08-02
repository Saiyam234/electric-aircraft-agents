"""JSON API for the agent oversight frontend.

This is the real backend: it reads/writes the exact same Cloudflare D1 +
Vectorize state as the agents themselves (via storage.py at the repo root —
kept in place rather than moved, since it's already tested and imported by
every agent script and by test_storage.py; moving it would be a repo-wide
import refactor with no functional upside). Nothing here renders HTML.

Run:  python3 backend/api.py     (serves on http://0.0.0.0:5001 by default;
override with the PORT/HOST env vars — Railway and similar platforms inject
PORT automatically).
The Next.js frontend (frontend/) talks to this over fetch() + CORS.
"""

import os
import re
import secrets
import sys
from collections import Counter
from datetime import datetime

from flask import Flask, Response, jsonify, request
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import storage  # noqa: E402
import run_console  # noqa: E402

app = Flask(__name__)
CORS(
    app,
    resources={r"/api/*": {"origins": "*"}},
    allow_headers=["Content-Type", "Authorization"],
)

URGENT_EVENTS = {"escalation"}

# Real data + real agent dispatch behind a single shared password, since this
# is a solo-owner tool, not a multi-user product. Unset locally (127.0.0.1
# is already private) — set both on Railway/prod or every route here is
# public to anyone with the link. Loud startup warning rather than a silent
# open door, since forgetting this is the realistic failure mode.
DASHBOARD_USER = os.environ.get("DASHBOARD_USER")
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD")
if not DASHBOARD_USER or not DASHBOARD_PASSWORD:
    print(
        "WARNING: DASHBOARD_USER/DASHBOARD_PASSWORD not set — every /api/* "
        "route is unauthenticated. Fine for local dev, not fine deployed."
    )


@app.before_request
def _require_dashboard_auth():
    if not DASHBOARD_USER or not DASHBOARD_PASSWORD:
        return None
    if request.method == "OPTIONS":
        return None  # CORS preflight — no credentials sent by the browser
    auth = request.authorization
    ok = (
        auth is not None
        and secrets.compare_digest(auth.username or "", DASHBOARD_USER)
        and secrets.compare_digest(auth.password or "", DASHBOARD_PASSWORD)
    )
    if not ok:
        return Response(
            "Authentication required",
            401,
            {"WWW-Authenticate": 'Basic realm="Electric Aircraft"'},
        )
    return None

# The 19 fixed agents per CLAUDE.md's roster (division, display name, script
# filename under agents/ or None if unbuilt, AGENT_NAME string in the audit
# log's `agent` column or None if unbuilt). Hand-maintained — no other single
# source of truth to derive it from.
ROSTER = [
    ("Orchestrator", "Orchestrator", "orchestrator_agent.py", "Orchestrator"),
    ("Knowledge Base", "Foundational Research Agent", "foundational_research_agent.py", "FoundationalResearchAgent"),
    ("Knowledge Base", "KB Manager", "kb_manager_agent.py", "KBManager"),
    ("Innovation", "Innovation Validator", "innovation_validator_agent.py", "InnovationValidator"),
    ("Concurrent Engineering Cluster", "Systems Engineer", "systems_engineer_agent.py", "SystemsEngineer"),
    ("Concurrent Engineering Cluster", "Configuration Synthesis Lead", "configuration_synthesis_lead_agent.py", "ConfigurationSynthesisLead"),
    ("Concurrent Engineering Cluster", "Math & Physics Engine", "math_physics_engine_agent.py", "MathPhysicsEngine"),
    ("Concurrent Engineering Cluster", "Airframe Engineer", "airframe_engineer_agent.py", "AirframeEngineer"),
    ("Concurrent Engineering Cluster", "Propulsion & Power Engineer", "propulsion_power_engineer_agent.py", "PropulsionPowerEngineer"),
    ("Concurrent Engineering Cluster", "Chief Integration Agent", "chief_integration_agent.py", "ChiefIntegrationAgent"),
    ("Concurrent Engineering Cluster", "Software Engineer", "software_engineer_agent.py", "SoftwareEngineer"),
    ("Concurrent Engineering Cluster", "Design Realization Agent", "design_realization_agent.py", "DesignRealizationAgent"),
    ("Manufacturing", "Manufacturing Manager", None, None),
    ("Verification & Validation", "Simulation Agent", "simulation_agent.py", "SimulationAgent"),
    ("Verification & Validation", "Physical Testing Agent", None, None),
    ("Assurance Gate", "Review & Critic", "review_critic_agent.py", "ReviewCritic"),
    ("Assurance Gate", "Safety & Risk", "safety_risk_agent.py", "SafetyRisk"),
    ("Assurance Gate", "Regulatory", "regulatory_agent.py", "Regulatory"),
    ("Literature", "Literature Agent", None, None),
]


def _parse_flags(description: str) -> dict:
    out = {}
    for token in description.split():
        if "=" in token:
            key, _, val = token.partition("=")
            out[key] = val
    return out


def _parse_kv(description: str) -> dict:
    out = {}
    for chunk in description.split(" | "):
        if ": " in chunk:
            key, _, val = chunk.partition(": ")
            out[key.strip()] = val.strip()
    return out


def _answered_decision_ids(events) -> set:
    answers = [e["description"] for e in events if e["event_type"] == "decision_answer"]
    return {a.split(" || ")[0].removeprefix("RE: ").strip() for a in answers}


def _run_durations(events) -> list:
    start_ts, end_ts = {}, {}
    for e in events:
        rid = _parse_flags(e["description"]).get("run_id")
        if not rid:
            continue
        if e["event_type"] == "agent_start":
            start_ts[rid] = e["timestamp"]
        elif e["event_type"] == "agent_end":
            end_ts[rid] = e["timestamp"]
    durations = []
    for rid, s in start_ts.items():
        t = end_ts.get(rid)
        if not t:
            continue
        try:
            durations.append((datetime.fromisoformat(t) - datetime.fromisoformat(s)).total_seconds())
        except ValueError:
            continue
    return durations


@app.route("/api/overview")
def overview():
    events = storage.get_audit_log(limit=500)
    requirements = storage.list_requirements(limit=200)
    baselines = storage.list_baselines(limit=40)

    try:
        kb_count = storage.get_kb_count()
    except Exception:
        kb_count = None

    runs = [e for e in events if e["event_type"] == "agent_end"]
    proposed = [r for r in requirements if r["status"] == "proposed"]
    answered = _answered_decision_ids(events)
    escalations = [e for e in events if e["event_type"] in URGENT_EVENTS]
    decisions = [e for e in events if e["event_type"] == "decision_request"]
    open_decisions = [d for d in decisions if _parse_kv(d["description"]).get("QUESTION", "") not in answered]

    chrono_runs = list(reversed(runs))
    costs, cum_cost, cum_runs, running = [], [], [], 0.0
    for i, e in enumerate(chrono_runs):
        c = 0.0
        for tok in e["description"].split():
            if tok.startswith("cost=$"):
                try:
                    c = float(tok[6:])
                except ValueError:
                    pass
        costs.append(c)
        running += c
        cum_cost.append(round(running, 4))
        cum_runs.append(i + 1)
    total_cost = round(sum(costs), 4)

    now = datetime.now()
    recent_runs, recent_cost = 0, 0.0
    for e, c in zip(chrono_runs, costs):
        try:
            ts = datetime.fromisoformat(e["timestamp"])
            if (now - ts.replace(tzinfo=None)).days <= 7:
                recent_runs += 1
                recent_cost += c
        except ValueError:
            pass

    error_flags = [_parse_flags(e["description"]) for e in runs]
    known = [f for f in error_flags if "is_error" in f]
    errored = [f for f in known if f.get("is_error") == "True"]
    success_rate = 100.0 * (1 - len(errored) / len(known)) if known else None

    durations = _run_durations(events)
    avg_runtime = sum(durations) / len(durations) if durations else None

    built_agents = [r for r in ROSTER if r[2]]
    hour = now.hour
    greeting = "Good morning" if hour < 12 else ("Good afternoon" if hour < 18 else "Good evening")

    if errored:
        status = {"level": "bad", "text": f"{len(errored)} agent run(s) errored — see Agents"}
    elif open_decisions or proposed:
        status = {"level": "warn", "text": f"{len(open_decisions)} decision(s) and {len(proposed)} requirement(s) waiting on you"}
    else:
        status = {"level": "ok", "text": "All tracked runs clean, nothing waiting on you"}

    return jsonify({
        "greeting": greeting,
        "status": status,
        "total_cost": total_cost,
        "recent_cost_7d": round(recent_cost, 4),
        "spend_series": cum_cost,
        "total_runs": len(runs),
        "recent_runs_7d": recent_runs,
        "run_series": cum_runs,
        "success_rate": success_rate,
        "known_run_count": len(known),
        "avg_runtime_seconds": avg_runtime,
        "timed_run_count": len(durations),
        "agents_built": len(built_agents),
        "roster_total": len(ROSTER),
        "open_decisions_count": len(open_decisions),
        "escalations_count": len(escalations),
        "proposed_requirements_count": len(proposed),
        "kb_count": kb_count,
        "baselines_count": len(baselines),
        "escalations": [
            {"agent": e["agent"], "timestamp": e["timestamp"], "description": e["description"]}
            for e in escalations[:6]
        ],
    })


@app.route("/api/roster")
def roster():
    events = storage.get_audit_log(limit=500)
    agent_ends_by_name, latest_output_by_name = {}, {}
    for e in events:
        if e["event_type"] == "agent_end":
            agent_ends_by_name.setdefault(e["agent"], []).append(e)
        elif e["event_type"] not in ("agent_start", "agent_end") and e["agent"] not in latest_output_by_name:
            latest_output_by_name[e["agent"]] = e

    result = []
    for division, display_name, script, log_name in ROSTER:
        if not script:
            result.append({
                "division": division, "name": display_name, "built": False,
                "status": "not_built", "run_count": 0, "error_count": 0,
                "unknown_count": 0, "latest_output": None, "latest_output_type": None,
            })
            continue
        ends = agent_ends_by_name.get(log_name, [])
        flagged = [(_parse_flags(e["description"]), e) for e in ends]
        errs = [e for f, e in flagged if f.get("is_error") == "True"]
        limits = [e for f, e in flagged if f.get("hit_turn_limit") == "True"]
        unknown_n = len([f for f, e in flagged if "is_error" not in f])
        if not ends:
            status = "not_run"
        elif errs:
            status = "error"
        elif limits:
            status = "turn_limit"
        else:
            status = "clean"
        latest = latest_output_by_name.get(log_name)
        result.append({
            "division": division, "name": display_name, "built": True,
            "status": status, "run_count": len(ends), "error_count": len(errs),
            "unknown_count": unknown_n,
            "latest_output": latest["description"] if latest else None,
            "latest_output_type": latest["event_type"] if latest else None,
        })
    return jsonify(result)


# log_name (audit_log's `agent` column, e.g. "ConfigurationSynthesisLead") ->
# display_name (e.g. "Configuration Synthesis Lead"), for every built agent.
_LOG_NAME_TO_DISPLAY = {log_name: display_name for _, display_name, _, log_name in ROSTER if log_name}

_BASELINE_MENTION_RE = re.compile(r"baseline[_\s]*(?:id)?\s*[=:#]?\s*(\d+)", re.IGNORECASE)
_REQUIREMENT_MENTION_RE = re.compile(r"requirement[s]?\s*#?\s*(\d+)", re.IGNORECASE)


def _artifact_mentions(description: str) -> list[str]:
    """Real artifacts named in an event's own description text — not a
    schema field (related_baseline_id/related_requirement_id exist in the
    audit_log table but no agent tool ever populates them, so every row has
    them NULL; the only real signal is the free text every agent already
    writes). Returns keys like "baseline 210" or "requirement 29"."""
    mentions = []
    for m in _BASELINE_MENTION_RE.finditer(description):
        mentions.append(f"baseline {m.group(1)}")
    for m in _REQUIREMENT_MENTION_RE.finditer(description):
        mentions.append(f"requirement {m.group(1)}")
    return mentions


@app.route("/api/agents/graph")
def agents_graph():
    """Real provenance, not the prescribed CLAUDE.md pipeline: which agent's
    real output another agent's real run actually touched, reconstructed by
    correlating which baseline/requirement numbers show up in whose event
    descriptions, in real chronological order. An edge only exists if two
    different agents' real events both named the same real artifact."""
    events = storage.get_audit_log(limit=1000)
    chrono = list(reversed(events))  # get_audit_log is DESC; oldest-first for real sequence

    by_artifact: dict[str, list[dict]] = {}
    for e in chrono:
        display_name = _LOG_NAME_TO_DISPLAY.get(e["agent"])
        if not display_name or e["event_type"] in ("agent_start", "agent_end"):
            continue
        for artifact in _artifact_mentions(e["description"]):
            by_artifact.setdefault(artifact, []).append({
                "agent": display_name, "timestamp": e["timestamp"],
                "event_id": e["id"], "description": e["description"],
            })

    edge_map: dict[tuple[str, str], dict] = {}
    for artifact, touches in by_artifact.items():
        for prev, cur in zip(touches, touches[1:]):
            if prev["agent"] == cur["agent"]:
                continue
            key = (prev["agent"], cur["agent"])
            edge = edge_map.setdefault(key, {
                "source": prev["agent"], "target": cur["agent"], "artifacts": {},
            })
            if artifact not in edge["artifacts"]:
                edge["artifacts"][artifact] = cur["event_id"]

    edges = [
        {
            "source": e["source"],
            "target": e["target"],
            "artifacts": sorted(e["artifacts"].keys(), key=lambda a: e["artifacts"][a]),
        }
        for e in edge_map.values()
    ]

    nodes = [
        {"division": division, "name": display_name, "built": bool(script)}
        for division, display_name, script, _ in ROSTER
    ]

    return jsonify({"nodes": nodes, "edges": edges})


@app.route("/api/decisions")
def decisions():
    events = storage.get_audit_log(limit=500)
    answered = _answered_decision_ids(events)
    all_decisions = [e for e in events if e["event_type"] == "decision_request"]
    open_decisions = []
    for d in all_decisions:
        fields = _parse_kv(d["description"])
        question = fields.get("QUESTION", d["description"])
        if question in answered:
            continue
        options = []
        try:
            import json
            options = json.loads(fields.get("OPTIONS", "[]"))
        except Exception:
            pass
        open_decisions.append({
            "agent": d["agent"], "timestamp": d["timestamp"], "question": question,
            "context": fields.get("CONTEXT"), "options": options,
        })
    return jsonify(open_decisions)


@app.route("/api/decisions/answer", methods=["POST"])
def answer_decision():
    body = request.get_json(force=True) or {}
    question = (body.get("question") or "").strip()
    answer_text = (body.get("answer") or "").strip()
    if not question or not answer_text:
        return jsonify({"error": "question and answer are required"}), 400
    storage.log_event("Saiyam", "decision_answer", f"RE: {question} || ANSWER: {answer_text}")
    return jsonify({"ok": True})


@app.route("/api/requirements")
def requirements():
    reqs = storage.list_requirements(limit=200)
    status_counts = Counter(r["status"] for r in reqs)
    proposed = [r for r in reqs if r["status"] == "proposed"]
    return jsonify({
        "status_counts": dict(status_counts),
        "proposed": proposed,
    })


@app.route("/api/requirements/<int:req_id>", methods=["POST"])
def decide_requirement(req_id):
    body = request.get_json(force=True) or {}
    decision = body.get("decision")
    if decision not in {"approved", "rejected"}:
        return jsonify({"error": "decision must be 'approved' or 'rejected'"}), 400
    storage.update_requirement_status(req_id, decision)
    storage.log_event("Saiyam", "requirement_decision", f"requirement #{req_id} -> {decision}")
    return jsonify({"ok": True})


@app.route("/api/baselines")
def baselines():
    rows = storage.list_baselines(limit=40)
    result = []
    for b in rows:
        try:
            stamped = storage.is_baseline_stamped(b["id"])
        except Exception:
            stamped = False
        result.append({**b, "stamped": stamped})
    return jsonify(result)


@app.route("/api/kb")
def kb():
    q = request.args.get("q", "").strip()
    try:
        if q:
            matches = storage.search_kb(q, top_k=20)
            rows = [{
                "id": m.get("id") or m.get("entry_id"),
                "text": (m.get("metadata", {}) or {}).get("text") or m.get("text") or "",
                "score": m.get("score"),
            } for m in matches]
        else:
            ids = storage.list_kb_ids(limit=15)
            entries = storage.get_kb_entries(ids) if ids else []
            rows = [{
                "id": e.get("id"),
                "text": (e.get("metadata") or {}).get("text", ""),
                "score": None,
            } for e in entries]
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502
    return jsonify(rows)


@app.route("/api/kb/count")
def kb_count():
    try:
        return jsonify({"total": storage.get_kb_count()})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502


@app.route("/api/logs")
def logs():
    limit = min(int(request.args.get("limit", 150)), 500)
    events = storage.get_audit_log(limit=limit)
    return jsonify([
        {"agent": e["agent"], "event_type": e["event_type"], "timestamp": e["timestamp"], "description": e["description"]}
        for e in events
    ])


@app.route("/api/agents/runnable")
def runnable_agents():
    """Every real, dispatchable agent, its real CLI input mode, and real
    historical cost stats computed from actual past runs — never a fabricated
    estimate. Agents with zero real runs simply have no cost hint yet."""
    events = storage.get_audit_log(limit=500)
    costs: dict[str, list[float]] = {}
    for e in events:
        if e["event_type"] != "agent_end":
            continue
        for tok in e["description"].split():
            if tok.startswith("cost=$"):
                try:
                    costs.setdefault(e["agent"], []).append(float(tok[6:]))
                except ValueError:
                    pass

    result = []
    for name, spec in run_console.RUNNABLE_AGENTS.items():
        vals = costs.get(name, [])
        result.append({
            "agent": name,
            "mode": spec["mode"],
            "run_count": len(vals),
            "avg_cost": round(sum(vals) / len(vals), 4) if vals else None,
            "min_cost": round(min(vals), 4) if vals else None,
            "max_cost": round(max(vals), 4) if vals else None,
        })
    return jsonify(result)


@app.route("/api/agents/run", methods=["POST"])
def start_agent_run():
    body = request.get_json(force=True) or {}
    agent = body.get("agent", "")
    user_input = body.get("input")
    result = run_console.start_job(agent, user_input)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route("/api/agents/run/<job_id>")
def get_agent_run(job_id):
    job = run_console.get_job(job_id)
    if job is None:
        return jsonify({"error": "unknown job_id"}), 404
    return jsonify(job)


@app.route("/api/agents/runs")
def list_agent_runs():
    return jsonify(run_console.list_jobs())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"API → http://{host}:{port}   (Ctrl+C to stop)")
    app.run(host=host, port=port, debug=False, threaded=True)
