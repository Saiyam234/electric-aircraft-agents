"""Engineering formula library — the single source of exact numbers for every agent.

WHY THIS IS SHARED, NOT OWNED BY ONE AGENT:

The first real run of the Wave 1 loop exposed the problem. Math & Physics Engine
had a calculator and used it correctly. Configuration Synthesis Lead had none, so
it did its arithmetic inline in its own reasoning — wing loading, stall speed,
cruise power, all worked out in prose. Spot-checking showed it happened to get
them right, but "the model was good at mental arithmetic that day" is not an
engineering control. Any agent that emits a number now computes it here.

Sharing also makes cross-validation meaningful: when Math & Physics checks
Configuration Synthesis Lead's work, both are running identical formulas, so a
disagreement is a real disagreement about inputs or assumptions rather than an
artifact of two different approximations.

Every formula is plain Python, unit-explicit in its parameter names, and
validated against published reference aircraft in test_engineering_math.py.
SI throughout: metres, kilograms, seconds, newtons, watts, pascals.
"""

from __future__ import annotations

import math

G = 9.80665  # m/s^2
RHO_SEA_LEVEL = 1.225  # kg/m^3, ISA sea level
NU_SEA_LEVEL = 1.46e-5  # m^2/s, kinematic viscosity of air, ISA sea level
SPEED_OF_SOUND = 340.29  # m/s, ISA sea level

# Lift on one semi-span of an elliptically-loaded wing acts at this fraction of
# the semi-span, measured from the root: 4/(3*pi).
ELLIPTIC_LIFT_CENTROID = 4.0 / (3.0 * math.pi)


# ---------------------------------------------------------------------------
# Geometry and basic sizing
# ---------------------------------------------------------------------------

def wing_loading(mass_kg: float, wing_area_m2: float) -> dict:
    return {
        "wing_loading_n_m2": (mass_kg * G) / wing_area_m2,
        "wing_loading_kg_m2": mass_kg / wing_area_m2,
    }


def aspect_ratio(wingspan_m: float, wing_area_m2: float) -> dict:
    return {"aspect_ratio": (wingspan_m**2) / wing_area_m2}


def mean_aerodynamic_chord(root_chord_m: float, tip_chord_m: float) -> dict:
    """MAC of a straight-tapered wing, plus where it sits spanwise. The MAC is
    the reference length for static margin and CG position."""
    taper = tip_chord_m / root_chord_m
    mac = (2.0 / 3.0) * root_chord_m * ((1.0 + taper + taper**2) / (1.0 + taper))
    return {"mac_m": mac, "taper_ratio": taper}


# ---------------------------------------------------------------------------
# Aerodynamics
# ---------------------------------------------------------------------------

def stall_speed(mass_kg: float, wing_area_m2: float, cl_max: float, air_density: float = RHO_SEA_LEVEL) -> dict:
    v = math.sqrt((2.0 * mass_kg * G) / (air_density * wing_area_m2 * cl_max))
    return {"stall_speed_ms": v, "stall_speed_kmh": v * 3.6}


def lift_coefficient_required(
    mass_kg: float, wing_area_m2: float, airspeed_ms: float, air_density: float = RHO_SEA_LEVEL
) -> dict:
    return {"cl_required": (2.0 * mass_kg * G) / (air_density * (airspeed_ms**2) * wing_area_m2)}


def induced_drag_coefficient(cl: float, aspect_ratio_value: float, oswald_efficiency: float = 0.8) -> dict:
    return {"cd_induced": (cl**2) / (math.pi * aspect_ratio_value * oswald_efficiency)}


def reynolds_number(airspeed_ms: float, chord_m: float, kinematic_viscosity: float = NU_SEA_LEVEL) -> dict:
    return {"reynolds_number": (airspeed_ms * chord_m) / kinematic_viscosity}


def level_flight_power(
    mass_kg: float,
    wing_area_m2: float,
    wingspan_m: float,
    airspeed_ms: float,
    cd0: float,
    oswald_efficiency: float = 0.8,
    air_density: float = RHO_SEA_LEVEL,
) -> dict:
    """Full cruise solve: CL, drag breakdown, L/D, and shaft power required."""
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


def best_glide_speed(
    mass_kg: float,
    wing_area_m2: float,
    wingspan_m: float,
    cd0: float,
    oswald_efficiency: float = 0.8,
    air_density: float = RHO_SEA_LEVEL,
) -> dict:
    """Speed for maximum L/D — where induced drag equals parasite drag. Also the
    best-glide speed after a power failure, which matters for failsafe planning."""
    ar = (wingspan_m**2) / wing_area_m2
    k = 1.0 / (math.pi * ar * oswald_efficiency)
    cl_opt = math.sqrt(cd0 / k)
    ld_max = cl_opt / (2.0 * cd0)
    v = math.sqrt((2.0 * mass_kg * G) / (air_density * wing_area_m2 * cl_opt))
    return {"best_glide_speed_ms": v, "cl_at_best_glide": cl_opt, "max_lift_to_drag": ld_max}


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------

def rate_of_climb(power_available_w: float, power_required_w: float, mass_kg: float) -> dict:
    """Excess power divided by weight. Negative means it cannot sustain level flight."""
    roc = (power_available_w - power_required_w) / (mass_kg * G)
    return {"rate_of_climb_ms": roc, "sustainable_level_flight": roc >= 0.0}


def thrust_to_weight(thrust_n: float, mass_kg: float) -> dict:
    """A VTOL needs T/W > 1 to lift off at all; ~1.5-2.0 is the usual band for
    authority to control attitude and reject gusts while hovering."""
    twr = thrust_n / (mass_kg * G)
    return {"thrust_to_weight": twr, "can_hover": twr > 1.0}


def turn_radius(airspeed_ms: float, bank_angle_deg: float) -> dict:
    rad = math.radians(bank_angle_deg)
    load_factor = 1.0 / math.cos(rad)
    return {
        "turn_radius_m": (airspeed_ms**2) / (G * math.tan(rad)),
        "load_factor_g": load_factor,
        "stall_speed_multiplier": math.sqrt(load_factor),
    }


# ---------------------------------------------------------------------------
# VTOL / rotor
# ---------------------------------------------------------------------------

def disk_area_from_rotors(rotor_diameter_m: float, rotor_count: float) -> dict:
    single = math.pi * ((rotor_diameter_m / 2.0) ** 2)
    return {"single_rotor_area_m2": single, "total_disk_area_m2": single * int(rotor_count)}


def hover_power(
    mass_kg: float, total_disk_area_m2: float, figure_of_merit: float = 0.7, air_density: float = RHO_SEA_LEVEL
) -> dict:
    """Momentum-theory hover power. Ideal induced power is a hard physical floor —
    no rotor beats it — so figure_of_merit (~0.6-0.75 for small rotors) scales it
    to something achievable."""
    thrust_n = mass_kg * G
    ideal_w = thrust_n * math.sqrt(thrust_n / (2.0 * air_density * total_disk_area_m2))
    return {
        "thrust_required_n": thrust_n,
        "disk_loading_n_m2": thrust_n / total_disk_area_m2,
        "ideal_hover_power_w": ideal_w,
        "estimated_hover_power_w": ideal_w / figure_of_merit,
    }


def rotor_tip_speed(rotor_diameter_m: float, rpm: float, speed_of_sound: float = SPEED_OF_SOUND) -> dict:
    """Tip Mach number. Past roughly M 0.7 a rotor gets loud and loses efficiency
    to compressibility — a real constraint on choosing small-diameter, high-RPM
    rotors to save space."""
    tip_ms = (rpm * 2.0 * math.pi / 60.0) * (rotor_diameter_m / 2.0)
    mach = tip_ms / speed_of_sound
    return {
        "tip_speed_ms": tip_ms,
        "tip_mach": mach,
        "compressibility_concern": mach > 0.7,
    }


def hover_endurance(usable_energy_wh: float, hover_power_w: float) -> dict:
    return {"hover_endurance_min": (usable_energy_wh / hover_power_w) * 60.0}


def transition_energy(hover_power_w: float, cruise_power_w: float, transition_seconds: float) -> dict:
    """Energy for one hover->cruise transition, approximated as the mean of the two
    power states. Conservative enough for budgeting; real transition power peaks
    above both and needs simulation to pin down."""
    mean_w = (hover_power_w + cruise_power_w) / 2.0
    return {"mean_transition_power_w": mean_w, "transition_energy_wh": mean_w * (transition_seconds / 3600.0)}


# ---------------------------------------------------------------------------
# Structures
# ---------------------------------------------------------------------------

def wing_root_bending_moment(mass_kg: float, wingspan_m: float, load_factor: float = 1.0) -> dict:
    """Root bending moment from an elliptically-loaded wing at a given load factor.
    This is the number that sizes the spar, and the load path whose failure is
    unrecoverable."""
    lift_per_semi_span_n = (mass_kg * G * load_factor) / 2.0
    arm_m = ELLIPTIC_LIFT_CENTROID * (wingspan_m / 2.0)
    return {
        "lift_per_semi_span_n": lift_per_semi_span_n,
        "lift_centroid_from_root_m": arm_m,
        "root_bending_moment_nm": lift_per_semi_span_n * arm_m,
    }


def spar_cap_second_moment(cap_area_m2: float, cap_separation_m: float) -> dict:
    """I for two spar caps separated by a web, ignoring the web's own contribution
    (standard conservative approximation: I ~= 2*A*(h/2)^2)."""
    return {"second_moment_m4": 2.0 * cap_area_m2 * ((cap_separation_m / 2.0) ** 2)}


def bending_stress(moment_nm: float, distance_from_neutral_axis_m: float, second_moment_m4: float) -> dict:
    stress_pa = (moment_nm * distance_from_neutral_axis_m) / second_moment_m4
    return {"bending_stress_pa": stress_pa, "bending_stress_mpa": stress_pa / 1e6}


def safety_factor(allowable_stress_mpa: float, actual_stress_mpa: float) -> dict:
    sf = allowable_stress_mpa / actual_stress_mpa
    return {"safety_factor": sf, "adequate_for_1_5": sf >= 1.5}


def cantilever_tip_deflection(
    load_n: float, length_m: float, youngs_modulus_pa: float, second_moment_m4: float
) -> dict:
    """Tip deflection of a cantilever under a tip point load (PL^3/3EI). A stiffness
    check, separate from strength — a spar can be strong enough and still flex too
    much for the control surfaces or rotor clearances to behave."""
    d = (load_n * (length_m**3)) / (3.0 * youngs_modulus_pa * second_moment_m4)
    return {"tip_deflection_m": d, "tip_deflection_mm": d * 1000.0}


# ---------------------------------------------------------------------------
# Weight, balance and stability
# ---------------------------------------------------------------------------

def center_of_gravity(masses_kg: list[float], positions_m: list[float]) -> dict:
    """Mass-weighted CG. positions_m are measured from a common datum (typically
    the nose), in the same order as masses_kg."""
    total = sum(masses_kg)
    moment = sum(m * x for m, x in zip(masses_kg, positions_m))
    return {"total_mass_kg": total, "cg_from_datum_m": moment / total, "total_moment_nm": moment * G}


def static_margin(neutral_point_m: float, cg_m: float, mac_m: float) -> dict:
    """Static margin as a fraction of MAC. Positive means statically stable in
    pitch. Conventional aircraft target roughly 5-15%; zero or negative requires
    active stabilisation to stay flyable."""
    sm = (neutral_point_m - cg_m) / mac_m
    return {
        "static_margin_fraction": sm,
        "static_margin_percent_mac": sm * 100.0,
        "statically_stable": sm > 0.0,
    }


# ---------------------------------------------------------------------------
# Propulsion and energy
# ---------------------------------------------------------------------------

def electrical_power_required(
    shaft_power_w: float,
    propeller_efficiency: float = 0.6,
    motor_efficiency: float = 0.85,
    esc_efficiency: float = 1.0,
) -> dict:
    """CRUISE electrical power: shaft power grossed up through the drivetrain.

    FOR FORWARD FLIGHT ONLY. Propeller efficiency is defined as (thrust x
    velocity) / shaft power, so it requires forward velocity and is undefined in
    hover. Passing hover shaft power here double-counts the rotor's aerodynamic
    losses, because hover_power's figure_of_merit already accounts for them —
    use hover_electrical_power instead.

    That is not a hypothetical: it happened. A configuration draft ran hover
    shaft power through this function, reported 306 W instead of 187 W, and the
    resulting energy budget appeared not to close. The error stood until the
    Propulsion & Power Engineer caught it in review.
    """
    chain = propeller_efficiency * motor_efficiency * esc_efficiency
    elec = shaft_power_w / chain
    return {
        "electrical_power_w": elec,
        "drivetrain_efficiency": chain,
        "losses_w": elec - shaft_power_w,
    }


def hover_electrical_power(
    hover_shaft_power_w: float, motor_efficiency: float = 0.85, esc_efficiency: float = 0.95
) -> dict:
    """HOVER electrical power: hover shaft power through motor and ESC only.

    Deliberately takes no propeller-efficiency argument. In hover the rotor's
    aerodynamic efficiency is already captured by figure_of_merit inside
    hover_power, so the only remaining losses are electrical.
    """
    chain = motor_efficiency * esc_efficiency
    elec = hover_shaft_power_w / chain
    return {
        "electrical_power_w": elec,
        "electrical_chain_efficiency": chain,
        "losses_w": elec - hover_shaft_power_w,
    }


def energy_for_endurance(power_w: float, endurance_min: float, usable_fraction: float = 0.8) -> dict:
    """Battery energy needed, derated because a pack's full nameplate capacity is
    not safely usable (see the KB's LiPo discharge-cutoff entries)."""
    usable_wh = power_w * (endurance_min / 60.0)
    return {"usable_energy_wh": usable_wh, "nameplate_energy_wh": usable_wh / usable_fraction}


def battery_pack_from_energy(
    nameplate_energy_wh: float, cell_count_series: float, specific_energy_wh_kg: float = 150.0
) -> dict:
    """Pack mass, capacity, and nominal voltage for a required energy. Uses the
    3.7 V/cell LiPo nominal from the knowledge base."""
    nominal_v = 3.7 * int(cell_count_series)
    return {
        "nominal_voltage_v": nominal_v,
        "capacity_ah": nameplate_energy_wh / nominal_v,
        "capacity_mah": (nameplate_energy_wh / nominal_v) * 1000.0,
        "estimated_pack_mass_kg": nameplate_energy_wh / specific_energy_wh_kg,
    }


def discharge_c_rate(power_w: float, capacity_ah: float, nominal_voltage_v: float) -> dict:
    """C-rate the pack must sustain. Hover usually sets this, and exceeding a
    pack's rating is a direct thermal-runaway path."""
    current_a = power_w / nominal_voltage_v
    return {"current_draw_a": current_a, "c_rate": current_a / capacity_ah}


def mission_energy_budget(
    hover_power_w: float,
    cruise_power_w: float,
    hover_time_s: float,
    cruise_time_s: float,
    reserve_fraction: float = 0.2,
) -> dict:
    """Full VTOL mission energy: hover segments plus cruise plus reserve. This is
    the check that catches a hover-driven mass spiral, where hover quietly eats
    the budget that cruise endurance was sized around."""
    hover_wh = hover_power_w * (hover_time_s / 3600.0)
    cruise_wh = cruise_power_w * (cruise_time_s / 3600.0)
    subtotal = hover_wh + cruise_wh
    total = subtotal * (1.0 + reserve_fraction)
    return {
        "hover_energy_wh": hover_wh,
        "cruise_energy_wh": cruise_wh,
        "subtotal_wh": subtotal,
        "total_with_reserve_wh": total,
        "hover_fraction_of_energy": hover_wh / subtotal,
    }


# name -> (function, required params, optional params with defaults, description)
FORMULAS: dict[str, tuple] = {
    # geometry / sizing
    "wing_loading": (wing_loading, ["mass_kg", "wing_area_m2"], {}, "Wing loading W/S"),
    "aspect_ratio": (aspect_ratio, ["wingspan_m", "wing_area_m2"], {}, "Wing aspect ratio b^2/S"),
    "mean_aerodynamic_chord": (
        mean_aerodynamic_chord,
        ["root_chord_m", "tip_chord_m"],
        {},
        "MAC and taper ratio — the reference length for CG and static margin",
    ),
    # aerodynamics
    "stall_speed": (
        stall_speed,
        ["mass_kg", "wing_area_m2", "cl_max"],
        {"air_density": RHO_SEA_LEVEL},
        "Stall speed from wing loading and CL_max",
    ),
    "lift_coefficient_required": (
        lift_coefficient_required,
        ["mass_kg", "wing_area_m2", "airspeed_ms"],
        {"air_density": RHO_SEA_LEVEL},
        "CL needed for level flight at a given speed",
    ),
    "induced_drag_coefficient": (
        induced_drag_coefficient,
        ["cl", "aspect_ratio_value"],
        {"oswald_efficiency": 0.8},
        "Induced drag coefficient CL^2/(pi*AR*e)",
    ),
    "reynolds_number": (
        reynolds_number,
        ["airspeed_ms", "chord_m"],
        {"kinematic_viscosity": NU_SEA_LEVEL},
        "Chord Reynolds number — decides which airfoil data applies",
    ),
    "level_flight_power": (
        level_flight_power,
        ["mass_kg", "wing_area_m2", "wingspan_m", "airspeed_ms", "cd0"],
        {"oswald_efficiency": 0.8, "air_density": RHO_SEA_LEVEL},
        "Full cruise solve: CL, CD, L/D, drag and shaft power required",
    ),
    "best_glide_speed": (
        best_glide_speed,
        ["mass_kg", "wing_area_m2", "wingspan_m", "cd0"],
        {"oswald_efficiency": 0.8, "air_density": RHO_SEA_LEVEL},
        "Speed for max L/D — also best glide after power loss",
    ),
    # performance
    "rate_of_climb": (
        rate_of_climb,
        ["power_available_w", "power_required_w", "mass_kg"],
        {},
        "Climb rate from excess power",
    ),
    "thrust_to_weight": (
        thrust_to_weight,
        ["thrust_n", "mass_kg"],
        {},
        "Thrust-to-weight ratio; VTOL needs >1 to lift, ~1.5-2 for control authority",
    ),
    "turn_radius": (
        turn_radius,
        ["airspeed_ms", "bank_angle_deg"],
        {},
        "Turn radius, load factor, and stall-speed penalty in a banked turn",
    ),
    # VTOL / rotor
    "disk_area_from_rotors": (
        disk_area_from_rotors,
        ["rotor_diameter_m", "rotor_count"],
        {},
        "Total rotor disk area from diameter and count",
    ),
    "hover_power": (
        hover_power,
        ["mass_kg", "total_disk_area_m2"],
        {"figure_of_merit": 0.7, "air_density": RHO_SEA_LEVEL},
        "Momentum-theory hover power and disk loading",
    ),
    "rotor_tip_speed": (
        rotor_tip_speed,
        ["rotor_diameter_m", "rpm"],
        {"speed_of_sound": SPEED_OF_SOUND},
        "Rotor tip speed and Mach — flags compressibility above ~M0.7",
    ),
    "hover_endurance": (
        hover_endurance,
        ["usable_energy_wh", "hover_power_w"],
        {},
        "How long the pack sustains hover",
    ),
    "transition_energy": (
        transition_energy,
        ["hover_power_w", "cruise_power_w", "transition_seconds"],
        {},
        "Approximate energy for one hover<->cruise transition",
    ),
    # structures
    "wing_root_bending_moment": (
        wing_root_bending_moment,
        ["mass_kg", "wingspan_m"],
        {"load_factor": 1.0},
        "Root bending moment (elliptical loading) — the number that sizes the spar",
    ),
    "spar_cap_second_moment": (
        spar_cap_second_moment,
        ["cap_area_m2", "cap_separation_m"],
        {},
        "Second moment of area for a two-cap spar",
    ),
    "bending_stress": (
        bending_stress,
        ["moment_nm", "distance_from_neutral_axis_m", "second_moment_m4"],
        {},
        "Bending stress sigma = M*c/I",
    ),
    "safety_factor": (
        safety_factor,
        ["allowable_stress_mpa", "actual_stress_mpa"],
        {},
        "Safety factor, with a 1.5 adequacy flag",
    ),
    "cantilever_tip_deflection": (
        cantilever_tip_deflection,
        ["load_n", "length_m", "youngs_modulus_pa", "second_moment_m4"],
        {},
        "Cantilever tip deflection PL^3/3EI — a stiffness check, not strength",
    ),
    # weight, balance, stability
    "center_of_gravity": (
        center_of_gravity,
        ["masses_kg", "positions_m"],
        {},
        "Mass-weighted CG from component masses and positions (both are lists)",
    ),
    "static_margin": (
        static_margin,
        ["neutral_point_m", "cg_m", "mac_m"],
        {},
        "Static margin as %MAC; positive means statically stable in pitch",
    ),
    # propulsion and energy
    "electrical_power_required": (
        electrical_power_required,
        ["shaft_power_w"],
        {"propeller_efficiency": 0.6, "motor_efficiency": 0.85, "esc_efficiency": 1.0},
        "CRUISE electrical power. NOT for hover — see hover_electrical_power",
    ),
    "hover_electrical_power": (
        hover_electrical_power,
        ["hover_shaft_power_w"],
        {"motor_efficiency": 0.85, "esc_efficiency": 0.95},
        "HOVER electrical power (motor+ESC only; figure_of_merit already covers rotor losses)",
    ),
    "energy_for_endurance": (
        energy_for_endurance,
        ["power_w", "endurance_min"],
        {"usable_fraction": 0.8},
        "Battery energy needed, derated for safe usable capacity",
    ),
    "battery_pack_from_energy": (
        battery_pack_from_energy,
        ["nameplate_energy_wh", "cell_count_series"],
        {"specific_energy_wh_kg": 150.0},
        "Pack mass, capacity and voltage for a required energy",
    ),
    "discharge_c_rate": (
        discharge_c_rate,
        ["power_w", "capacity_ah", "nominal_voltage_v"],
        {},
        "C-rate the pack must sustain — hover usually sets this",
    ),
    "mission_energy_budget": (
        mission_energy_budget,
        ["hover_power_w", "cruise_power_w", "hover_time_s", "cruise_time_s"],
        {"reserve_fraction": 0.2},
        "Full VTOL mission energy incl. reserve; catches hover-driven mass spiral",
    ),
}

# Params that take a list rather than a scalar, so the dispatcher knows not to
# coerce them to float.
LIST_PARAMS = {"masses_kg", "positions_m"}


def format_formula_docs() -> str:
    """Generated from FORMULAS so prompts can never advertise a formula that
    doesn't exist, or miss one that does."""
    lines = []
    for name, (_fn, required, optional, description) in FORMULAS.items():
        opt = "".join(f", {k}={v:g} (optional)" for k, v in optional.items())
        lines.append(f"- {name}({', '.join(required)}{opt}) — {description}")
    return "\n".join(lines)


def calculate(formula: str, params: dict) -> dict:
    """Validates and dispatches one formula call.

    Returns {"ok": True, "result": {...}} or {"ok": False, "error": "..."} — never
    raises, so a tool wrapping this can always hand the model something useful to
    correct rather than dying mid-run.
    """
    entry = FORMULAS.get(formula)
    if entry is None:
        return {"ok": False, "error": f"unknown formula {formula!r}. Available: {sorted(FORMULAS)}"}
    fn, required, optional, _description = entry

    if not isinstance(params, dict):
        return {"ok": False, "error": "params must be a JSON object"}

    missing = [p for p in required if p not in params]
    if missing:
        return {"ok": False, "error": f"{formula} is missing required params: {missing}"}
    unknown = [k for k in params if k not in required and k not in optional]
    if unknown:
        return {"ok": False, "error": f"{formula} got unknown params {unknown}; accepts {required + list(optional)}"}

    coerced: dict = {}
    for key, value in params.items():
        if key in LIST_PARAMS:
            if not isinstance(value, list) or not value:
                return {"ok": False, "error": f"{formula}: {key} must be a non-empty list of numbers"}
            try:
                coerced[key] = [float(v) for v in value]
            except (TypeError, ValueError):
                return {"ok": False, "error": f"{formula}: every entry of {key} must be numeric"}
        else:
            try:
                coerced[key] = float(value)
            except (TypeError, ValueError):
                return {"ok": False, "error": f"{formula}: {key} must be numeric, got {value!r}"}

    if "masses_kg" in coerced and "positions_m" in coerced:
        if len(coerced["masses_kg"]) != len(coerced["positions_m"]):
            return {"ok": False, "error": "masses_kg and positions_m must be the same length"}

    # Physical-plausibility gate. Some params are legitimately zero or negative
    # (a CG datum offset, a power difference), so only the ones that are
    # nonsensical at <= 0 are checked.
    must_be_positive = {
        "mass_kg", "wing_area_m2", "wingspan_m", "airspeed_ms", "cl_max", "chord_m",
        "root_chord_m", "tip_chord_m", "rotor_diameter_m", "rotor_count", "rpm",
        "total_disk_area_m2", "capacity_ah", "nominal_voltage_v", "cell_count_series",
        "second_moment_m4", "cap_area_m2", "cap_separation_m", "youngs_modulus_pa",
        "length_m", "mac_m", "actual_stress_mpa", "allowable_stress_mpa",
        "usable_energy_wh", "nameplate_energy_wh", "hover_power_w",
    }
    bad = [k for k, v in coerced.items() if k in must_be_positive and isinstance(v, float) and v <= 0]
    if bad:
        return {"ok": False, "error": f"{formula}: these params must be positive: {bad}"}

    try:
        result = fn(**coerced)
    except (ValueError, ZeroDivisionError, OverflowError) as exc:
        return {"ok": False, "error": f"{formula} failed: {exc}"}

    rounded = {k: (_round_sig(v, 6) if isinstance(v, float) else v) for k, v in result.items()}
    return {"ok": True, "result": rounded}


def _round_sig(x: float, sig: int) -> float:
    """Round to `sig` significant figures, not decimal places.

    A plain round(x, 6) silently zeros out any legitimately small SI-unit
    result — moments of area in m^4 are routinely ~1e-9, well under a fixed
    6-decimal-place cutoff. That happened for real: spar_cap_second_moment
    returned 0.0 for a real 1.96e-9 m^4 result during Simulation Agent's
    first verified run, and the agent silently substituted the (correct, by
    luck) right-looking value in its next tool call instead of reading it
    from the tool — the exact "mental arithmetic that happened to be right"
    failure mode this module exists to make impossible.
    """
    if x == 0 or math.isnan(x) or math.isinf(x):
        return x
    digits = sig - 1 - math.floor(math.log10(abs(x)))
    return round(x, int(digits))
