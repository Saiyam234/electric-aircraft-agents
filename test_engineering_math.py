"""Validation suite for engineering_math.py.

Unlike test_storage.py these are pure-Python and hit no network, so they run
instantly and for free. Every formula is checked either against a published
reference aircraft, an independently-derived closed form, or an exact analytic
identity — not against whatever the code happens to currently return, which
would only prove the code equals itself.

Run: pytest test_engineering_math.py -v
"""

import math

import pytest

import engineering_math as em

# Cessna 172S, published figures: span 11.0 m, wing area 16.2 m^2, MTOW ~1111 kg,
# published aspect ratio 7.32, clean stall ~48-53 kt (24.7-27.3 m/s).
C172 = {"mass_kg": 1111.0, "wing_area_m2": 16.2, "wingspan_m": 11.0, "cl_max": 1.5}


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

def test_aspect_ratio_matches_published_c172():
    ar = em.aspect_ratio(C172["wingspan_m"], C172["wing_area_m2"])["aspect_ratio"]
    assert ar == pytest.approx(7.32, abs=0.2), f"C172 AR should be ~7.32, got {ar}"


def test_mac_of_rectangular_wing_equals_its_chord():
    """Analytic identity: an untapered wing's MAC is exactly its chord."""
    mac = em.mean_aerodynamic_chord(0.25, 0.25)
    assert mac["mac_m"] == pytest.approx(0.25)
    assert mac["taper_ratio"] == pytest.approx(1.0)


def test_mac_of_tapered_wing_lies_between_tip_and_root():
    mac = em.mean_aerodynamic_chord(2.0, 1.0)["mac_m"]
    assert 1.0 < mac < 2.0
    # Closed form for taper 0.5: (2/3)*2*(1.75/1.5)
    assert mac == pytest.approx((2.0 / 3.0) * 2.0 * (1.75 / 1.5))


# ---------------------------------------------------------------------------
# Aerodynamics
# ---------------------------------------------------------------------------

def test_stall_speed_matches_published_c172_range():
    v = em.stall_speed(C172["mass_kg"], C172["wing_area_m2"], C172["cl_max"])["stall_speed_ms"]
    assert 24.0 <= v <= 29.0, f"C172 clean stall should be ~25-27 m/s, got {v}"


def test_stall_speed_scales_as_sqrt_of_wing_loading():
    """KB-cited relationship: doubling W/S raises stall speed ~41% (sqrt(2))."""
    base = em.stall_speed(2.5, 0.35, 1.2)["stall_speed_ms"]
    doubled = em.stall_speed(5.0, 0.35, 1.2)["stall_speed_ms"]
    assert doubled / base == pytest.approx(math.sqrt(2.0), rel=1e-6)


def test_lift_coefficient_required_is_consistent_with_stall_speed():
    """At exactly stall speed, the CL required must equal CL_max."""
    v_stall = em.stall_speed(2.5, 0.35, 1.2)["stall_speed_ms"]
    cl = em.lift_coefficient_required(2.5, 0.35, v_stall)["cl_required"]
    assert cl == pytest.approx(1.2, rel=1e-6)


def test_level_flight_power_matches_hand_computed_drag_polar():
    """Independent recomputation of the parabolic drag polar."""
    r = em.level_flight_power(2.5, 0.35, 1.4, 15.0, 0.03, oswald_efficiency=0.75)
    ar = 1.4**2 / 0.35
    q = 0.5 * 1.225 * 15.0**2
    cl = (2.5 * em.G) / (q * 0.35)
    cd = 0.03 + cl**2 / (math.pi * ar * 0.75)
    assert r["cl_required"] == pytest.approx(cl)
    assert r["cd_total"] == pytest.approx(cd)
    assert r["power_required_w"] == pytest.approx(cd * q * 0.35 * 15.0)


def test_best_glide_matches_standard_ld_max_closed_form():
    """L/D_max = 0.5*sqrt(1/(k*CD0)) — a different derivation than the code's."""
    cd0, e = 0.03, 0.75
    r = em.best_glide_speed(2.5, 0.35, 1.4, cd0, oswald_efficiency=e)
    ar = 1.4**2 / 0.35
    k = 1.0 / (math.pi * ar * e)
    assert r["max_lift_to_drag"] == pytest.approx(0.5 * math.sqrt(1.0 / (k * cd0)))


def test_best_glide_speed_is_above_stall():
    v_stall = em.stall_speed(2.5, 0.35, 1.2)["stall_speed_ms"]
    v_bg = em.best_glide_speed(2.5, 0.35, 1.4, 0.03)["best_glide_speed_ms"]
    assert v_bg > v_stall


def test_reynolds_number_small_uav_regime():
    """KB: small UAVs sit at chord Re <= ~3e5. A 0.25 m chord at 15 m/s should land there."""
    re = em.reynolds_number(15.0, 0.25)["reynolds_number"]
    assert 1e5 < re < 3e5


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------

def test_rate_of_climb_flags_insufficient_power():
    assert em.rate_of_climb(50.0, 80.0, 2.5)["sustainable_level_flight"] is False
    assert em.rate_of_climb(120.0, 80.0, 2.5)["sustainable_level_flight"] is True


def test_thrust_to_weight_hover_threshold():
    assert em.thrust_to_weight(24.0, 2.5)["can_hover"] is False  # below weight
    assert em.thrust_to_weight(40.0, 2.5)["can_hover"] is True


def test_turn_radius_and_load_factor_at_60_degrees():
    """A 60-degree bank is exactly 2 g, and raises stall speed by sqrt(2)."""
    r = em.turn_radius(15.0, 60.0)
    assert r["load_factor_g"] == pytest.approx(2.0, rel=1e-6)
    assert r["stall_speed_multiplier"] == pytest.approx(math.sqrt(2.0), rel=1e-6)


# ---------------------------------------------------------------------------
# VTOL / rotor
# ---------------------------------------------------------------------------

def test_hover_power_matches_real_2kg_quadcopter():
    """A 2 kg quad on 4x10-inch props really does draw roughly 150-250 W hovering."""
    disk = em.disk_area_from_rotors(0.254, 4)["total_disk_area_m2"]
    p = em.hover_power(2.0, disk)["estimated_hover_power_w"]
    assert 140.0 <= p <= 260.0, f"expected ~150-250 W, got {p}"


def test_ideal_hover_power_is_a_floor_below_estimated():
    disk = em.disk_area_from_rotors(0.254, 4)["total_disk_area_m2"]
    r = em.hover_power(2.0, disk, figure_of_merit=0.7)
    assert r["ideal_hover_power_w"] < r["estimated_hover_power_w"]


def test_hover_power_rises_as_disk_area_shrinks():
    """The core physical trade: smaller rotors mean higher disk loading and
    disproportionately more hover power. This is what drives the mass spiral."""
    big = em.hover_power(2.5, em.disk_area_from_rotors(0.33, 4)["total_disk_area_m2"])
    small = em.hover_power(2.5, em.disk_area_from_rotors(0.20, 2)["total_disk_area_m2"])
    assert small["estimated_hover_power_w"] > 2.0 * big["estimated_hover_power_w"]


def test_rotor_tip_mach_flags_compressibility():
    assert em.rotor_tip_speed(0.254, 8000)["compressibility_concern"] is False
    assert em.rotor_tip_speed(0.60, 12000)["compressibility_concern"] is True


def test_mission_energy_budget_exposes_hover_dominance():
    """90 s of hover at 250 W against 15 min of cruise at 70 W — hover should be a
    large share despite being a fraction of the time."""
    r = em.mission_energy_budget(250.0, 70.0, 90.0, 900.0)
    assert r["hover_fraction_of_energy"] > 0.25
    assert r["total_with_reserve_wh"] > r["subtotal_wh"]


# ---------------------------------------------------------------------------
# Structures
# ---------------------------------------------------------------------------

def test_wing_root_bending_moment_hand_check():
    r = em.wing_root_bending_moment(2.5, 1.4)
    expected_arm = (4.0 / (3.0 * math.pi)) * 0.7
    assert r["lift_centroid_from_root_m"] == pytest.approx(expected_arm)
    assert r["root_bending_moment_nm"] == pytest.approx((2.5 * em.G / 2.0) * expected_arm)


def test_bending_moment_scales_linearly_with_load_factor():
    m1 = em.wing_root_bending_moment(2.5, 1.4, load_factor=1.0)["root_bending_moment_nm"]
    m4 = em.wing_root_bending_moment(2.5, 1.4, load_factor=4.0)["root_bending_moment_nm"]
    assert m4 == pytest.approx(4.0 * m1)


def test_spar_stress_chain_is_self_consistent():
    """Full chain: moment -> section -> stress -> safety factor."""
    moment = em.wing_root_bending_moment(2.5, 1.4, load_factor=4.0)["root_bending_moment_nm"]
    inertia = em.spar_cap_second_moment(1e-4, 0.03)["second_moment_m4"]
    stress = em.bending_stress(moment, 0.015, inertia)["bending_stress_mpa"]
    assert stress > 0
    # Against a conservative ~600 MPa CFRP allowable this should be comfortable.
    assert em.safety_factor(600.0, stress)["adequate_for_1_5"] is True


def test_deflection_scales_with_cube_of_length():
    """PL^3/3EI — doubling span should raise tip deflection 8x."""
    args = dict(load_n=12.0, youngs_modulus_pa=70e9, second_moment_m4=4.5e-8)
    d1 = em.cantilever_tip_deflection(length_m=0.7, **args)["tip_deflection_m"]
    d2 = em.cantilever_tip_deflection(length_m=1.4, **args)["tip_deflection_m"]
    assert d2 == pytest.approx(8.0 * d1, rel=1e-6)


# ---------------------------------------------------------------------------
# Weight, balance, stability
# ---------------------------------------------------------------------------

def test_center_of_gravity_hand_check():
    r = em.center_of_gravity([1.0, 2.0], [0.0, 1.5])
    assert r["total_mass_kg"] == pytest.approx(3.0)
    assert r["cg_from_datum_m"] == pytest.approx(1.0)


def test_cg_of_symmetric_masses_is_the_midpoint():
    r = em.center_of_gravity([1.0, 1.0], [0.2, 0.8])
    assert r["cg_from_datum_m"] == pytest.approx(0.5)


def test_static_margin_sign_and_magnitude():
    stable = em.static_margin(0.30, 0.27, 0.25)
    assert stable["statically_stable"] is True
    assert stable["static_margin_percent_mac"] == pytest.approx(12.0)
    # CG behind the neutral point is statically unstable.
    assert em.static_margin(0.30, 0.33, 0.25)["statically_stable"] is False


# ---------------------------------------------------------------------------
# Propulsion and energy
# ---------------------------------------------------------------------------

def test_electrical_power_exceeds_shaft_power():
    r = em.electrical_power_required(36.8)
    assert r["electrical_power_w"] > 36.8
    assert r["losses_w"] == pytest.approx(r["electrical_power_w"] - 36.8)


def test_hover_electrical_power_does_not_double_count_rotor_losses():
    """Regression test for a real error that reached a configuration baseline.

    Hover shaft power was run through electrical_power_required, which applies
    propeller efficiency — but hover_power's figure_of_merit already accounts
    for the rotor's aerodynamic losses. The double count reported 306 W instead
    of 187 W and made the energy budget appear not to close.
    """
    shaft = em.hover_power(2.5, 0.502655)["estimated_hover_power_w"]

    wrong = em.electrical_power_required(shaft, propeller_efficiency=0.6, motor_efficiency=0.85)
    right = em.hover_electrical_power(shaft, motor_efficiency=0.88, esc_efficiency=0.95)

    assert right["electrical_power_w"] == pytest.approx(186.9, abs=1.0)
    assert wrong["electrical_power_w"] == pytest.approx(306.4, abs=1.0)
    # The whole point: the correct hover figure is far below the double-counted one.
    assert right["electrical_power_w"] < wrong["electrical_power_w"] * 0.7


def test_hover_electrical_power_takes_no_propeller_efficiency():
    """The guard is structural: you cannot pass propeller_efficiency to the hover
    path even by mistake, because it isn't a parameter."""
    result = em.calculate(
        "hover_electrical_power", {"hover_shaft_power_w": 156.27, "propeller_efficiency": 0.6}
    )
    assert result["ok"] is False
    assert "unknown params" in result["error"]


def test_battery_pack_capacity_matches_energy_and_voltage():
    r = em.battery_pack_from_energy(135.0, 4)
    assert r["nominal_voltage_v"] == pytest.approx(14.8)
    assert r["capacity_ah"] * r["nominal_voltage_v"] == pytest.approx(135.0)


def test_discharge_c_rate_hand_check():
    """250 W from a 14.8 V, 2.0 Ah pack = 16.9 A = 8.4C."""
    r = em.discharge_c_rate(250.0, 2.0, 14.8)
    assert r["current_draw_a"] == pytest.approx(250.0 / 14.8)
    assert r["c_rate"] == pytest.approx((250.0 / 14.8) / 2.0)


def test_energy_derating_accounts_for_unusable_capacity():
    r = em.energy_for_endurance(70.0, 20.0, usable_fraction=0.8)
    assert r["nameplate_energy_wh"] == pytest.approx(r["usable_energy_wh"] / 0.8)


# ---------------------------------------------------------------------------
# Dispatcher: validation and error handling
# ---------------------------------------------------------------------------

def test_calculate_dispatches_valid_call():
    r = em.calculate("wing_loading", {"mass_kg": 2.5, "wing_area_m2": 0.35})
    assert r["ok"] is True
    assert r["result"]["wing_loading_n_m2"] == pytest.approx(70.05, abs=0.1)


def test_calculate_does_not_zero_out_small_si_results():
    """Regression test: a fixed round(x, 6) silently zeroed out real small
    SI-unit results (moments of area routinely ~1e-9 m^4), and during
    Simulation Agent's first real verified run the model quietly substituted
    the correct-looking value into its next tool call instead of reading it
    from a tool result that said 0.0 — exactly the "mental arithmetic that
    happened to be right" failure mode this module exists to prevent.
    calculate() must round by significant figures, not decimal places."""
    r = em.calculate("spar_cap_second_moment", {"cap_area_m2": 2e-5, "cap_separation_m": 0.014})
    assert r["ok"] is True
    assert r["result"]["second_moment_m4"] == pytest.approx(1.96e-9, rel=1e-3)
    assert r["result"]["second_moment_m4"] != 0.0


@pytest.mark.parametrize(
    "formula,params,expected_fragment",
    [
        ("nonexistent", {}, "unknown formula"),
        ("stall_speed", {"mass_kg": 2.5}, "missing required params"),
        ("wing_loading", {"mass_kg": 2.5, "wing_area_m2": 0.35, "bogus": 1}, "unknown params"),
        ("wing_loading", {"mass_kg": "heavy", "wing_area_m2": 0.35}, "must be numeric"),
        ("wing_loading", {"mass_kg": 0, "wing_area_m2": 0.35}, "must be positive"),
        ("center_of_gravity", {"masses_kg": [1.0], "positions_m": [0.0, 1.0]}, "same length"),
        ("center_of_gravity", {"masses_kg": [], "positions_m": []}, "non-empty list"),
    ],
)
def test_calculate_rejects_bad_input(formula, params, expected_fragment):
    r = em.calculate(formula, params)
    assert r["ok"] is False
    assert expected_fragment in r["error"]


def test_calculate_never_raises_on_hostile_input():
    """The dispatcher must always return a correctable error, never blow up an
    agent mid-run."""
    for params in [{"mass_kg": float("inf"), "wing_area_m2": 0.35}, {"mass_kg": 1e308, "wing_area_m2": 1e-308}]:
        result = em.calculate("wing_loading", params)
        assert isinstance(result, dict) and "ok" in result


def test_formula_docs_cover_every_registered_formula():
    """The generated docs are what prompts show the model — if one drifts out,
    the model is being told about a formula it can't call, or missing one it can."""
    docs = em.format_formula_docs()
    for name in em.FORMULAS:
        assert f"- {name}(" in docs


def test_list_params_are_actually_used_by_a_registered_formula():
    referenced = {p for _fn, req, opt, _d in em.FORMULAS.values() for p in list(req) + list(opt)}
    assert em.LIST_PARAMS <= referenced
