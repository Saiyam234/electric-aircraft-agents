# wing_planform.py
# Fusion 360 Python API script - WING PLANFORM ONLY
#
# Source of numbers (do not edit here; regenerate from storage if baseline changes):
#   Baseline 210, version v0.1-config-draft-1785704111 (2026-08-02)
#     wingspan_m      = 1.40   (MATCHES decided target, D1 event 117, 2026-07-29)
#     wing_area_m2    = 0.290
#     root_chord_m    = 0.230
#     tip_chord_m     = 0.184
#     taper_ratio     = 0.80
#     mac_m           = 0.207852
#     aspect_ratio    = 6.75862
#   Airfoil (Airframe Engineer review, event 92): SD7003, CL_max = 1.0
#
# SCOPE LIMITS (deliberate):
#   * Wing planform only. No fuselage, tail, booms, or lift rotors — VTOL
#     architecture is not selected yet, so those cannot be drawn honestly.
#   * Straight leading edge. No sweep is defined anywhere real; not invented here.
#   * Flat extrusion as a planform placeholder. A true airfoil-lofted wing
#     requires real SD7003 (x/c, y/c) coordinate data lofted between root and
#     tip sections — that is a follow-up pass, not this one.
#
# Usage in Fusion 360:
#   Scripts and Add-Ins -> Scripts -> + (Create) -> Python -> point at this file.
#   Then Run. All units below are centimeters at the API level; Fusion's
#   internal length unit is cm.

import adsk.core
import adsk.fusion
import adsk.cam
import traceback

# --- Real numbers from baseline 210 (meters) ---
WINGSPAN_M     = 1.40
ROOT_CHORD_M   = 0.230
TIP_CHORD_M    = 0.184
# Placeholder thickness for the flat planform extrusion. NOT a real airfoil
# thickness — SD7003 t/c = 8.5% would give ~19.6 mm at root, but that only
# means something once the real airfoil is lofted. Kept small and obvious.
PLACEHOLDER_THICKNESS_M = 0.005

# Fusion API internal length unit is centimeters.
M_TO_CM = 100.0
SEMI_SPAN_CM = (WINGSPAN_M / 2.0) * M_TO_CM
ROOT_CHORD_CM = ROOT_CHORD_M * M_TO_CM
TIP_CHORD_CM  = TIP_CHORD_M  * M_TO_CM
THICKNESS_CM  = PLACEHOLDER_THICKNESS_M * M_TO_CM


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface

        # Create a fresh document so we don't clobber whatever is open.
        doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        root_comp = design.rootComponent

        # Sketch the trapezoidal half-planform on XZ plane.
        # Convention: X = chordwise (leading edge at X=0, trailing edge toward +X).
        #             Z = spanwise (centerline at Z=0, tip at Z=+semi-span).
        # Straight leading edge along Z axis (no sweep specified anywhere real).
        sketches = root_comp.sketches
        xz_plane = root_comp.xZConstructionPlane
        sketch = sketches.add(xz_plane)
        sketch.name = 'WingPlanform_Half_Baseline210'

        lines = sketch.sketchCurves.sketchLines

        # Four corners of the half-planform trapezoid.
        # (Fusion sketch points are 3D but the sketch is 2D on its own plane.)
        p_root_le = adsk.core.Point3D.create(0.0,            0.0,          0.0)
        p_root_te = adsk.core.Point3D.create(ROOT_CHORD_CM,  0.0,          0.0)
        p_tip_te  = adsk.core.Point3D.create(TIP_CHORD_CM,   SEMI_SPAN_CM, 0.0)
        p_tip_le  = adsk.core.Point3D.create(0.0,            SEMI_SPAN_CM, 0.0)

        lines.addByTwoPoints(p_root_le, p_root_te)   # root chord
        lines.addByTwoPoints(p_root_te, p_tip_te)    # trailing edge
        lines.addByTwoPoints(p_tip_te,  p_tip_le)    # tip chord
        lines.addByTwoPoints(p_tip_le,  p_root_le)   # leading edge (straight)

        # Extrude the trapezoid as a flat placeholder body.
        # A real SD7003-lofted wing would replace this extrude with a loft
        # between two airfoil section sketches (root + tip), using real
        # SD7003 (x/c, y/c) coordinates scaled to ROOT_CHORD_CM and
        # TIP_CHORD_CM respectively. That is a follow-up pass.
        prof = sketch.profiles.item(0)
        extrudes = root_comp.features.extrudeFeatures
        ext_input = extrudes.createInput(
            prof,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        )
        distance = adsk.core.ValueInput.createByReal(THICKNESS_CM)
        ext_input.setDistanceExtent(False, distance)
        half_wing = extrudes.add(ext_input)

        # Mirror the half-wing across XY (Z=0) plane to get the full wing.
        mirror_feats = root_comp.features.mirrorFeatures
        input_bodies = adsk.core.ObjectCollection.create()
        for body in half_wing.bodies:
            input_bodies.add(body)
        mirror_input = mirror_feats.createInput(input_bodies, root_comp.xYConstructionPlane)
        mirror_feats.add(mirror_input)

        if ui:
            ui.messageBox(
                'Wing planform generated from baseline 210.\n'
                'Span 1.40 m, root 0.230 m, tip 0.184 m (taper 0.8).\n'
                'Airfoil: SD7003 (planform only in this pass — real airfoil '
                'loft is a follow-up requiring SD7003 coordinate data).'
            )

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
