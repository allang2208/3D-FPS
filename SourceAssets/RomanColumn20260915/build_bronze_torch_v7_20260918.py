"""Torch v7 (runs INSIDE the running editor):

  python Tools/AssetPipeline/ue_python_exec.py --script SourceAssets/RomanColumn20260915/build_bronze_torch_v7_20260918.py

User feedback driving v7:
  1. "surface graininess is wrong, I want a smooth bronze surface" -> the v6 material was the
     cause, not the mesh: a 1024 FFT micro-normal (dense random tangent-space noise) sat on
     MP_NORMAL and a 24x/3-level noise drove roughness 0.25..0.55 per texel. Metal + per-texel
     normal + per-texel roughness = sandpaper sparkle. v7 removes the micro normal entirely and
     keeps only ONE low-frequency mask (2 octaves) for a subtle patina tint and roughness drift;
     roughness band 0.16..0.30 over a smooth lathe = polished bronze.
  2. "the model still has room to improve" -> denser lathe (cup 96 / stem 64 segments), longer
     sampled profiles instead of straight chords, a real foot + neck + lip bead on the cup, a
     forged bracket (mount shoe, tapered bar, bosses and rivet studs on the diamond plates) and
     a proper clamp sleeve where the arm meets the stem.

Contracts kept from v6 (so the six placed actors and the level transform stay valid):
  local origin = column axis, bracket projects +X, arm plane at local z=0, collar r21.8/t2.4
  hugs the r~21 shaft, cup lip ~local z+42, tail tip ~local z-44.

No level or map work happens here: the running editor is shared with other sessions.
"""

import time

import unreal

SV = unreal.ModelingService
MEL = unreal.MaterialEditingLibrary
D = "/Game/Props/RomanColumn20260915"
TORCH = D + "/SM_BronzeTorch"
BRONZE = D + "/M_Bronze"
PATINA = D + "/T_BronzePatina"
LOG = []


def log(m):
    print("[tv7] " + m)


def do(label, result):
    ok = getattr(result, "success", None)
    LOG.append((label, ok))
    log("%-16s %s" % (label, ok))
    return result


def tf(x=0.0, y=0.0, z=0.0, pitch=0.0, yaw=0.0):
    t = unreal.Transform()
    t.translation = unreal.Vector(x, y, z)
    t.rotation = unreal.Rotator(0.0, pitch, yaw).quaternion()
    t.scale3d = unreal.Vector(1.0, 1.0, 1.0)
    return t


def wait(path, timeout=25.0):
    end = time.time() + timeout
    while time.time() < end:
        a = unreal.EditorAssetLibrary.load_asset(path)
        if a:
            return a
        time.sleep(0.3)
    return None


def save_pkg(path):
    """Remote-execution context: EditorAssetLibrary.save_* can report False, save_packages is real."""
    package = unreal.load_package(path)
    if package is None:
        return False
    try:
        ok = unreal.EditorLoadingAndSavingUtils.save_packages([package], False)
    except Exception as exc:  # noqa: BLE001
        log("save_packages failed on %s: %s" % (path, exc))
        ok = False
    if not ok:
        ok = unreal.EditorAssetLibrary.save_loaded_asset(unreal.EditorAssetLibrary.load_asset(path))
    log("save %-34s %s" % (path.split("/")[-1], ok))
    return ok


# ------------------------------------------------------------------ 1. low-frequency mask
# 2 octaves only: v6's 5-octave mask put fine colour speckle into the base colour.
do("patina_tex", SV.create_noise_texture(PATINA, 1024, 1024, 3.0, 2, 0.5, 5150, True))
patina_tex = wait(PATINA)

# ------------------------------------------------------------------ 2. smooth bronze material
bronze = None
if unreal.EditorAssetLibrary.does_asset_exist(BRONZE):
    bronze = unreal.EditorAssetLibrary.load_asset(BRONZE)
else:
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    bronze = tools.create_asset("M_Bronze", D, unreal.Material, unreal.MaterialFactoryNew())

# copy the list first: deleting while iterating the live expression set is unsafe here
for expr in list(MEL.get_material_expressions(bronze) or []):
    try:
        MEL.delete_material_expression(bronze, expr)
    except Exception as exc:  # noqa: BLE001
        log("delete_material_expression unavailable (%s); falling back to delete-all" % exc)
        MEL.delete_all_material_expressions(bronze)
        break

body = MEL.create_material_expression(bronze, unreal.MaterialExpressionVectorParameter, -1000, -340)
body.set_editor_property("parameter_name", "BronzeBody")
body.set_editor_property("default_value", unreal.LinearColor(0.56, 0.36, 0.16, 1.0))

patina_color = MEL.create_material_expression(bronze, unreal.MaterialExpressionVectorParameter, -1000, -180)
patina_color.set_editor_property("parameter_name", "BronzePatinaColor")
patina_color.set_editor_property("default_value", unreal.LinearColor(0.22, 0.36, 0.30, 1.0))

mask = MEL.create_material_expression(bronze, unreal.MaterialExpressionTextureSampleParameter2D, -1000, 20)
mask.set_editor_property("parameter_name", "PatinaMask")
if patina_tex:
    mask.set_editor_property("texture", patina_tex)

patina_strength = MEL.create_material_expression(bronze, unreal.MaterialExpressionScalarParameter, -1000, 300)
patina_strength.set_editor_property("parameter_name", "BronzePatinaStrength")
patina_strength.set_editor_property("default_value", 0.18)

mask_scaled = MEL.create_material_expression(bronze, unreal.MaterialExpressionMultiply, -720, 180)
mask_scaled.set_editor_property("const_b", 1.0)

rough_min = MEL.create_material_expression(bronze, unreal.MaterialExpressionScalarParameter, -720, -40)
rough_min.set_editor_property("parameter_name", "BronzeRoughMin")
rough_min.set_editor_property("default_value", 0.16)

rough_max = MEL.create_material_expression(bronze, unreal.MaterialExpressionScalarParameter, -720, 380)
rough_max.set_editor_property("parameter_name", "BronzeRoughMax")
rough_max.set_editor_property("default_value", 0.30)

metal = MEL.create_material_expression(bronze, unreal.MaterialExpressionConstant, -520, 480)
metal.set_editor_property("r", 1.0)

color_mix = MEL.create_material_expression(bronze, unreal.MaterialExpressionLinearInterpolate, -420, -260)
rough_mix = MEL.create_material_expression(bronze, unreal.MaterialExpressionLinearInterpolate, -420, 220)

MEL.connect_material_expressions(mask, "R", mask_scaled, "A")
MEL.connect_material_expressions(patina_strength, "", mask_scaled, "B")
MEL.connect_material_expressions(body, "", color_mix, "A")
MEL.connect_material_expressions(patina_color, "", color_mix, "B")
MEL.connect_material_expressions(mask_scaled, "", color_mix, "Alpha")
MEL.connect_material_expressions(rough_min, "", rough_mix, "A")
MEL.connect_material_expressions(rough_max, "", rough_mix, "B")
MEL.connect_material_expressions(mask_scaled, "", rough_mix, "Alpha")
MEL.connect_material_property(color_mix, "", unreal.MaterialProperty.MP_BASE_COLOR)
MEL.connect_material_property(rough_mix, "", unreal.MaterialProperty.MP_ROUGHNESS)
MEL.connect_material_property(metal, "", unreal.MaterialProperty.MP_METALLIC)
# MP_NORMAL intentionally left unconnected: v6's micro normal was the graininess.
MEL.recompile_material(bronze)
save_pkg(BRONZE)
log("material rebuilt: no micro normal, roughness 0.16..0.30 over one 2-octave mask")

# ------------------------------------------------------------------ 3. torch geometry (v7)
t = SV.create_mesh().handle

# 3.1 column collar (fit unchanged: shaft r~21, collar minor 2.4 at major 21.8)
do("collar", SV.append_torus(t, tf(0, 0, 0), 21.8, 2.4, 48, 12, "Base", 0))

# 3.2 forged bracket: shoe at the shaft, tapered bar, diamond plates with bosses + studs.
# The bar runs x22..50 so it enters the clamp sleeve at the stem (x50); the tip is thinner.
do("arm_shoe", SV.append_box(t, tf(22.5, 0, 0), 5.0, 3.4, 3.4, 0, 0, 0, "Center", 0))
do("arm_bar", SV.append_box(t, tf(33.0, 0, 0), 22.0, 2.2, 2.2, 0, 0, 0, "Center", 0))
do("arm_tip", SV.append_box(t, tf(47.0, 0, 0), 6.0, 1.7, 1.7, 0, 0, 0, "Center", 0))

do("plate_front", SV.append_box(t, tf(21.0, 0, 0, pitch=45.0), 11.0, 1.3, 11.0, 0, 0, 0, "Center", 0))
do("boss_front", SV.append_box(t, tf(21.0, 0, 0, pitch=45.0), 5.0, 1.9, 5.0, 0, 0, 0, "Center", 0))
do("plate_rear", SV.append_box(t, tf(33.5, 0, 0, pitch=45.0), 7.6, 1.2, 7.6, 0, 0, 0, "Center", 0))
do("boss_rear", SV.append_box(t, tf(33.5, 0, 0, pitch=45.0), 3.6, 1.8, 3.6, 0, 0, 0, "Center", 0))

# Rivet studs on the plate points (spheres, so no axis conversion is involved).
# A square plate of side S rotated 45 degrees about Y puts its corners at
# (+-S/sqrt2, 0) and (0, +-S/sqrt2) in the XZ plane, not at (+-S/2, +-S/2).
for i, (dx, dz) in enumerate(((6.9, 0.0), (-6.9, 0.0), (0.0, 6.9), (0.0, -6.9))):
    do("rivet_f%d" % i, SV.append_sphere(t, tf(21.0 + dx, 0.0, dz), 0.85, 8, 12, "Center", 0))
for i, (dx, dz) in enumerate(((4.8, 0.0), (-4.8, 0.0), (0.0, 4.8), (0.0, -4.8))):
    do("rivet_r%d" % i, SV.append_sphere(t, tf(33.5 + dx, 0.0, dz), 0.70, 8, 12, "Center", 0))

# 3.3 turned stem: droplet tail, four beads, flare into the cup seat
stem = [(0.00, -44.0), (1.10, -43.4), (2.30, -41.6), (3.60, -38.2), (4.30, -34.0),
        (4.20, -30.0), (3.50, -26.2), (2.40, -23.4), (1.90, -21.0), (2.60, -19.6),
        (1.90, -18.2), (1.75, -16.4), (1.60, -14.0), (2.70, -12.4), (1.75, -10.6),
        (1.60, -8.0), (1.55, -5.6), (2.60, -4.2), (1.70, -2.6), (1.60, -0.5),
        (1.70, 1.2), (2.90, 2.6), (1.90, 4.0), (1.85, 6.0), (2.10, 8.0),
        (3.60, 10.4), (5.60, 12.0), (0.00, 12.0)]
do("stem", SV.append_revolve_polygon(t, tf(50, 0, 0), stem, 0.0, 64, 360.0, 0))

# 3.4 clamp sleeve + ring where the arm grabs the stem
do("clamp", SV.append_cylinder(t, tf(50.0, 0.0, -3.4), 3.5, 6.8, 32, 0, True, "Center", 0))
do("joint_ring", SV.append_torus(t, tf(50.0, 0.0, 13.0), 4.5, 0.9, 40, 10, "Base", 0))

# 3.5 cup: foot, neck, flared bowl, lip bead, real inner cavity
cup = [(0.00, 11.6), (6.40, 11.6), (6.60, 12.6), (5.20, 14.2), (4.90, 15.6), (6.20, 17.6),
       (8.40, 20.4), (10.60, 24.0), (12.80, 28.4), (14.60, 33.2), (15.60, 36.8),
       (16.10, 39.6), (16.50, 41.4), (16.30, 42.4), (15.30, 42.6), (14.60, 41.4),
       (13.60, 38.0), (11.40, 33.0), (8.60, 27.0), (5.60, 21.0), (3.00, 16.4),
       (1.40, 14.2), (0.00, 13.6)]
do("cup", SV.append_revolve_polygon(t, tf(50, 0, 0), cup, 0.0, 96, 360.0, 0))
do("cup_lip", SV.append_torus(t, tf(50.0, 0.0, 41.6), 16.35, 0.75, 64, 10, "Base", 0))

info = SV.get_mesh_info(t)
log("v7: tris=%s comps=%s open=%s closed=%s" % (
    info.triangle_count, info.connected_components, info.open_border_edges, info.is_closed))
log("bbox x %.1f..%.1f y %.1f..%.1f z %.1f..%.1f" % (
    info.bounds_min.x, info.bounds_max.x, info.bounds_min.y, info.bounds_max.y,
    info.bounds_min.z, info.bounds_max.z))
ok_geom = info.is_closed and info.open_border_edges == 0
ok_bounds = (abs(info.bounds_min.z + 44.0) < 0.6 and abs(info.bounds_max.z - 42.6) < 0.6
             and abs(info.bounds_min.x + 24.2) < 0.6 and abs(info.bounds_max.x - 66.5) < 0.6)

do("uv", SV.auto_uv(t, "XAtlas", 0))
do("save", SV.save_mesh_to_static_mesh(t, TORCH, True, True, False, True))
SV.release_mesh(t)
if wait(TORCH):
    do("collision", SV.generate_collision(TORCH, "ConvexHulls", 6, 25, True))
    do("material", SV.set_asset_materials(TORCH, BRONZE, True))

log("geometry_ok=%s bounds_ok=%s steps=%d failed=%s" % (
    ok_geom, ok_bounds, len(LOG), [e[0] for e in LOG if e[1] is False]))
log("RESULT: " + ("PASS" if ok_geom and ok_bounds and not [e for e in LOG if e[1] is False] else "CHECK"))
