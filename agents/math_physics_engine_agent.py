"""Math & Physics Engine (Concurrent Engineering Cluster, per CLAUDE.md).

Aerodynamic, structural, and thermal calculation, plus flight-mechanics math.
Wave 1 scope: validate a drafted configuration's numbers — does the sizing
actually close, or are the figures internally inconsistent?

DESIGN POINT: the arithmetic happens in Python, never in the model.

Language models are unreliable at multi-step numerical work, and a plausible
-looking wrong number is the worst possible output for an agent whose entire
job is being correct about numbers. So the formulas below are real Python, and
the model's job is to decide WHICH calculation to run, supply the inputs, and
interpret the result. Same reasoning as kb_manager_agent doing its cosine
similarity in Python rather than asking the model to eyeball it.

The formula registry is also the single source of truth for the prompt's
documentation — FORMULA_DOCS is generated from it, so the two cannot drift
apart and the model can never be told a formula exists that doesn't.

Usage:
    python3 -m agents.math_physics_engine_agent
"""

import argparse
import json
import math

import anyio

import agent_runtime
import storage
from claude_agent_sdk import create_sdk_mcp_server, tool

AGENT_NAME = "MathPhysicsEngine"

G = 9.80665  # m/s^2
RHO_SEA_LEVEL = 1.225  # kg/m^3, ISA sea level
NU_SEA_LEVEL = 1.46e-5  # m^2/s, kinematic viscosity of air at ISA sea level


def _wing_loading(mass_kg: float, wing_area_m2: float) -> dict:
    return {
        "wing_loading_n_m2": (mass_kg * G) / wing_area_m2,
        "wing_loading_kg_m2": mass_kg / wing_area_m2,
    }


def _aspect_ratio(wingspan_m: float, wing_area_m2: float) -> dict:
    return {"aspect_ratio": (wingspan_m**2) / wing_area_m2}


def _stall_speed(mass_kg: float, wing_area_m2: float, cl_max: float, air_density: float = RHO_SEA_LEVEL) -> dict:
    v = math.sqrt((2.0 * mass_kg * G) / (air_density * wing_area_m2 * cl_max))
    return {"stall_speed_ms": v, "stall_speed_kmh": v * 3.6}


def _lift_coefficient_required(
    mass_kg: float, wing_area_m2: float, airspeed_ms: float, air_density: float = RHO_SEA_LEVEL
) -> dict:
    cl = (2.0 * mass_kg * G) / (air_density * (airspeed_ms**2) * wing_area_m2)
    return {"cl_required": cl}


def _induced_drag_coefficient(cl: float, aspect_ratio: float, oswald_efficiency: float = 0.8) -> dict:
    return {"cd_induced": (cl**2) / (math.pi * aspect_ratio * oswald_efficiency)}


def _reynolds_number(airspeed_ms: float, chord_m: float, kinematic_viscosity: float = NU_SEA_LEVEL) -> dict:
    return {"reynolds_number": (airspeed_ms * chord_m) / kinematic_viscosity}


def _level_flight_power(
    mass_kg: float,
    wing_area_m2: float,
    wingspan_m: float,
    airspeed_ms: float,
    cd0: float,
    oswald_efficiency: float = 0.8,
    air_density: float = RHO_SEA_LEVEL,
) -> dict:
    ar = (wingspan_m**2) / wing_area_m2
    q = 0.5 * air_density * (airspeed_ms**2)
    cl = (mass_kg * G) / (q * wing_area_m2)
    cd_i = (cl**2) / (math.pi * ar * oswald_efficiency)
    cd = cd0 + cd_i
    drag_n = cd * q * wing_area_m2
    return {
        "aspect_ratio": ar,
        "cl_required": cl,
        "cd_induced": cd_i,
        "cd_total": cd,
        "lift_to_drag": cl / cd,
        "drag_n": drag_n,
        "power_required_w": drag_n * airspeed_ms,
    }


def _hover_power(
    mass_kg: float,
    total_disk_area_m2: float,
    figure_of_merit: float = 0.7,
    air_density: float = RHO_SEA_LEVEL,
) -> dict:
    """Momentum-theory hover power. Ideal induced power is a hard physical floor —
    a real rotor always needs more, hence figure_of_merit (~0.6-0.75 typical small rotors)."""
    thrust_n = mass_kg * G
    ideal_w = thrust_n * math.sqrt(thrust_n / (2.0 * air_density * total_disk_area_m2))
    return {
        "thrust_required_n": thrust_n,
        "disk_loading_n_m2": thrust_n / total_disk_area_m2,
        "ideal_hover_power_w": ideal_w,
        "estimated_hover_power_w": ideal_w / figure_of_merit,
    }


def _disk_area_from_rotors(rotor_diameter_m: float, rotor_count: float) -> dict:
    single = math.pi * ((rotor_diameter_m / 2.0) ** 2)
    return {"single_rotor_area_m2": single, "total_disk_area_m2": single * int(rotor_count)}


def _energy_for_endurance(power_w: float, endurance_min: float, usable_fraction: float = 0.8) -> dict:
    """Battery energy needed, accounting for the fact you cannot safely use a pack's
    full nameplate capacity (see the KB's LiPo discharge-cutoff entries)."""
    usable_wh = power_w * (endurance_min / 60.0)
    return {"usable_energy_wh": usable_wh, "nameplate_energy_wh": usable_wh / usable_fraction}


# name -> (function, required params, optional params with defaults, one-line description)
FORMULAS = {
    "wing_loading": (_wing_loading, ["mass_kg", "wing_area_m2"], {}, "Wing loading W/S"),
    "aspect_ratio": (_aspect_ratio, ["wingspan_m", "wing_area_m2"], {}, "Wing aspect ratio b^2/S"),
    "stall_speed": (
        _stall_speed,
        ["mass_kg", "wing_area_m2", "cl_max"],
        {"air_density": RHO_SEA_LEVEL},
        "Stall speed from wing loading and CL_max",
    ),
    "lift_coefficient_required": (
        _lift_coefficient_required,
        ["mass_kg", "wing_area_m2", "airspeed_ms"],
        {"air_density": RHO_SEA_LEVEL},
        "CL needed for level flight at a given speed",
    ),
    "induced_drag_coefficient": (
        _induced_drag_coefficient,
        ["cl", "aspect_ratio"],
        {"oswald_efficiency": 0.8},
        "Induced drag coefficient CL^2/(pi*AR*e)",
    ),
    "reynolds_number": (
        _reynolds_number,
        ["airspeed_ms", "chord_m"],
        {"kinematic_viscosity": NU_SEA_LEVEL},
        "Chord Reynolds number — decides which airfoil data applies",
    ),
    "level_flight_power": (
        _level_flight_power,
        ["mass_kg", "wing_area_m2", "wingspan_m", "airspeed_ms", "cd0"],
        {"oswald_efficiency": 0.8, "air_density": RHO_SEA_LEVEL},
        "Full cruise solve: CL, CD, L/D, drag and power required",
    ),
    "hover_power": (
        _hover_power,
        ["mass_kg", "total_disk_area_m2"],
        {"figure_of_merit": 0.7, "air_density": RHO_SEA_LEVEL},
        "Momentum-theory hover power and disk loading (VTOL)",
    ),
    "disk_area_from_rotors": (
        _disk_area_from_rotors,
        ["rotor_diameter_m", "rotor_count"],
        {},
        "Total rotor disk area from diameter and count",
    ),
    "energy_for_endurance": (
        _energy_for_endurance,
        ["power_w", "endurance_min"],
        {"usable_fraction": 0.8},
        "Battery energy needed, derated for safe usable capacity",
    ),
}


def _format_formula_docs() -> str:
    """Generated from FORMULAS so the prompt can never document a formula that
    doesn't exist, or miss one that does."""
    lines = []
    for name, (_fn, required, optional, description) in FORMULAS.items():
        opt = "".join(f", {k}={v:g} (optional)" for k, v in optional.items())
        lines.append(f"- {name}({', '.join(required)}{opt}) — {description}")
    return "\n".join(lines)


FORMULA_DOCS = _format_formula_docs()


@tool(
    "calculate",
    "Run an exact engineering calculation in Python. formula is a name from the list in the prompt; "
    "params_json is a JSON object of its arguments. Never do this arithmetic yourself.",
    {"formula": str, "params_json": str},
)
async def calculate_tool(args):
    name = args["formula"]
    entry = FORMULAS.get(name)
    if entry is None:
        return {
            "content": [
                {"type": "text", "text": f"[REJECTED] unknown formula {name!r}. Available: {sorted(FORMULAS)}"}
            ],
            "is_error": True,
        }
    fn, required, optional, _description = entry

    try:
        params = json.loads(args["params_json"])
    except json.JSONDecodeError as exc:
        return {"content": [{"type": "text", "text": f"[REJECTED] params_json is not valid JSON: {exc}"}], "is_error": True}
    if not isinstance(params, dict):
        return {"content": [{"type": "text", "text": "[REJECTED] params_json must be a JSON object"}], "is_error": True}

    missing = [p for p in required if p not in params]
    if missing:
        return {
            "content": [{"type": "text", "text": f"[REJECTED] {name} is missing required params: {missing}"}],
            "is_error": True,
        }
    unknown = [k for k in params if k not in required and k not in optional]
    if unknown:
        return {
            "content": [
                {"type": "text", "text": f"[REJECTED] {name} got unknown params {unknown}; accepts {required + list(optional)}"}
            ],
            "is_error": True,
        }

    try:
        numeric = {k: float(v) for k, v in params.items()}
    except (TypeError, ValueError) as exc:
        return {"content": [{"type": "text", "text": f"[REJECTED] all params must be numeric: {exc}"}], "is_error": True}
    if any(v <= 0 for k, v in numeric.items() if k in required):
        return {
            "content": [{"type": "text", "text": f"[REJECTED] {name}: required params must be positive, got {numeric}"}],
            "is_error": True,
        }

    try:
        result = fn(**numeric)
    except (ValueError, ZeroDivisionError, OverflowError) as exc:
        return {"content": [{"type": "text", "text": f"[REJECTED] {name} failed: {exc}"}], "is_error": True}

    rounded = {k: round(v, 4) for k, v in result.items()}
    return {"content": [{"type": "text", "text": json.dumps({"formula": name, "inputs": numeric, "result": rounded})}]}


@tool("list_baselines", "List baselines so you can pick the configuration to validate", {})
async def list_baselines_tool(args):
    return {"content": [{"type": "text", "text": json.dumps(storage.list_baselines(limit=50), default=str)}]}


@tool("get_baseline", "Fetch one baseline's full configuration by id", {"baseline_id": float})
async def get_baseline_tool(args):
    try:
        baseline = storage.get_baseline(int(args["baseline_id"]))
    except ValueError as exc:
        return {"content": [{"type": "text", "text": f"[REJECTED] {exc}"}], "is_error": True}
    return {"content": [{"type": "text", "text": json.dumps(baseline, default=str)}]}


@tool("search_kb", "Semantic search the knowledge base for a coefficient, limit, or formula", {"query": str})
async def search_kb_tool(args):
    matches = storage.search_kb(args["query"], top_k=5)
    trimmed = [
        {"id": m["id"], "text": m["metadata"].get("text", ""), "source_title": m["metadata"].get("source_title", "")}
        for m in matches
    ]
    return {"content": [{"type": "text", "text": json.dumps(trimmed, default=str)}]}


@tool("log_event", "Log a summary event to the audit log", {"event_type": str, "description": str})
async def log_event_tool(args):
    storage.log_event(AGENT_NAME, args["event_type"], args["description"])
    return {"content": [{"type": "text", "text": "Logged event"}]}


storage_server = create_sdk_mcp_server(
    name="storage",
    tools=[calculate_tool, list_baselines_tool, get_baseline_tool, search_kb_tool, log_event_tool],
)

ALLOWED_TOOLS = [
    "mcp__storage__calculate",
    "mcp__storage__list_baselines",
    "mcp__storage__get_baseline",
    "mcp__storage__search_kb",
    "mcp__storage__log_event",
]

PROMPT = f"""You are the Math & Physics Engine for a multi-agent electric aircraft engineering
project. Your job is to check whether a drafted configuration's numbers actually hold up —
does the sizing close, or is it internally inconsistent?

The aircraft is a 1:8-scale, electric, fully autonomous eVTOL. The VTOL architecture is
deliberately not yet selected, so treat hover requirements generically (total rotor disk
area), not as a specific arrangement.

ABSOLUTE RULE — NEVER DO ARITHMETIC YOURSELF:
Every number you report must come from a calculate tool call. Do not multiply, divide, or
take a square root in your head or in your reasoning text and present the result. If you
need a number, call calculate. If no formula fits, say so explicitly rather than estimating.
A confidently-stated wrong number is the worst thing you can produce.

AVAILABLE FORMULAS (exact parameter names required):
{FORMULA_DOCS}

Steps:
1. Call list_baselines, then get_baseline on the most recent configuration draft (the
   version string starts with "v0.1-config-draft"). If no such baseline exists, say so
   plainly and stop — do not invent a configuration to check.
2. Use search_kb to pull the real coefficients you need — CL_max for a candidate airfoil,
   realistic CD0, Oswald efficiency, battery energy density, LiPo usable-discharge limits.
   Use evidence-backed values, and state which value you used and where it came from. Where
   you must assume something, label it an assumption explicitly.
3. Work through the configuration with calculate: wing loading, aspect ratio, stall speed,
   Reynolds number at cruise (this decides whether standard airfoil data even applies at
   this scale), cruise power, hover power, and the battery energy implied by the target
   endurance.
4. Compare against the configuration's own claimed numbers. Flag every disagreement, and say
   which figure you believe and why.

Pay particular attention to whether hover power is survivable: for small eVTOLs, hover
power usually dominates the energy budget and is where optimistic sizing quietly fails.

When done, call log_event ONCE with event_type="configuration_validated" summarizing what
checked out, what didn't, and the single biggest risk to the sizing closing. Then give a
clear written verdict: does this configuration close, and what would have to change?
"""


async def main():
    argparse.ArgumentParser(description="Math & Physics Engine — configuration validation pass").parse_args()

    options = agent_runtime.build_options(
        system_prompt=(
            "You are the Math & Physics Engine from a multi-agent electric aircraft "
            "engineering project. You never do arithmetic yourself — every number comes "
            "from a calculate tool call. State assumptions explicitly. Be precise."
        ),
        storage_server=storage_server,
        allowed_tools=ALLOWED_TOOLS,
        max_turns=50,
    )

    stats = await agent_runtime.run_agent(AGENT_NAME, options, PROMPT)
    print(f"\n===== DONE — cost ${stats['cost']:.4f} =====")


if __name__ == "__main__":
    anyio.run(main)
