"""Roman domed pavilion, white marble, voxel-aligned (20 cm grid).

Layers (all multiples of 20):
  stylobate disc   diameter 640 x 20                 (32 x 1 voxels)
  8 roman columns  260 tall, 80 base, ring radius 240 (columns sit at z=20)
  ring entablature annulus r 280-320, 40 tall        (z 280-320)
  dome cap         ring 280-320 + hemisphere r 280 + finial r 20 (z 320-660)
"""

import math
import time

import unreal

SV = unreal.ModelingService
DIR = "/Game/Props/RomanColumn20260915"
STYLO, RING, DOME = DIR + "/SM_PavilionStylobate_20", DIR + "/SM_PavilionRing_20", DIR + "/SM_PavilionDome_20"
COLUMN = DIR + "/SM_RomanColumn_Detailed"
MARBLE = DIR + "/M_WhiteMarble_V2"
VEIN, DETAIL = DIR + "/T_MarbleV2_Veins", DIR + "/T_MarbleV2_Detail"
V = 20.0
ORIGIN = (1350.0, 0.0)
LOG = []


def log(m):
    print("[pav] " + m)


def tf(x=0.0, y=0.0, z=0.0):
    t = unreal.Transform()
    t.translation = unreal.Vector(x, y, z)
    t.rotation = unreal.Rotator(0.0, 0.0, 0.0).quaternion()
    t.scale3d = unreal.Vector(1.0, 1.0, 1.0)
    return t


def v2(r, z):
    return unreal.Vector2D(r, z)


def do(label, result):
    ok = getattr(result, "success", None)
    LOG.append((label, ok))
    log("%-16s %s" % (label, ok))
    return result


def wait(path, timeout=15.0):
    end = time.time() + timeout
    while time.time() < end:
        a = unreal.EditorAssetLibrary.load_asset(path)
        if a:
            return a
        time.sleep(0.3)
    return None


def publish(handle, path, method="ConvexHulls", hulls=8):
    do("uv", SV.auto_uv(handle, "XAtlas", 0))
    do("save", SV.save_mesh_to_static_mesh(handle, path, True, True, False, True))
    SV.release_mesh(handle)
    if wait(path):
        do("collision", SV.generate_collision(path, method, hulls, 25, True))
        do("material", SV.set_asset_materials(path, MARBLE, True))


# ------------------------------------------------------------------ marble V2
do("vein_tex", SV.create_noise_texture(VEIN, 1024, 1024, 4.0, 6, 0.62, 4242, True))
do("detail_tex", SV.create_noise_texture(DETAIL, 1024, 1024, 24.0, 3, 0.45, 4243, True))
vein_tex, detail_tex = wait(VEIN), wait(DETAIL)
tools = unreal.AssetToolsHelpers.get_asset_tools()
library = unreal.MaterialEditingLibrary
marble = unreal.EditorAssetLibrary.load_asset(MARBLE)
if not marble:
    marble = tools.create_asset("M_WhiteMarble_V2", DIR, unreal.Material, unreal.MaterialFactoryNew())
library.delete_all_material_expressions(marble)
body = library.create_material_expression(marble, unreal.MaterialExpressionVectorParameter, -900, -300)
body.set_editor_property("parameter_name", "MarbleBody")
body.set_editor_property("default_value", unreal.LinearColor(0.94, 0.93, 0.91, 1.0))
vein = library.create_material_expression(marble, unreal.MaterialExpressionVectorParameter, -900, -120)
vein.set_editor_property("parameter_name", "MarbleVein")
vein.set_editor_property("default_value", unreal.LinearColor(0.66, 0.67, 0.70, 1.0))
n1 = library.create_material_expression(marble, unreal.MaterialExpressionTextureSampleParameter2D, -900, 60)
n1.set_editor_property("parameter_name", "VeinNoise")
n1.set_editor_property("texture", vein_tex)
n2 = library.create_material_expression(marble, unreal.MaterialExpressionTextureSampleParameter2D, -900, 260)
n2.set_editor_property("parameter_name", "DetailNoise")
n2.set_editor_property("texture", detail_tex)
mix = library.create_material_expression(marble, unreal.MaterialExpressionLinearInterpolate, -600, -220)
r1 = library.create_material_expression(marble, unreal.MaterialExpressionScalarParameter, -600, 120)
r1.set_editor_property("parameter_name", "MarbleRoughnessMin")
r1.set_editor_property("default_value", 0.12)
r2 = library.create_material_expression(marble, unreal.MaterialExpressionScalarParameter, -600, 260)
r2.set_editor_property("parameter_name", "MarbleRoughnessMax")
r2.set_editor_property("default_value", 0.28)
rmix = library.create_material_expression(marble, unreal.MaterialExpressionLinearInterpolate, -340, 200)
library.connect_material_expressions(n1, "R", mix, "Alpha")
library.connect_material_expressions(body, "", mix, "A")
library.connect_material_expressions(vein, "", mix, "B")
library.connect_material_expressions(n2, "R", rmix, "Alpha")
library.connect_material_expressions(r1, "", rmix, "A")
library.connect_material_expressions(r2, "", rmix, "B")
library.connect_material_property(mix, "", unreal.MaterialProperty.MP_BASE_COLOR)
library.connect_material_property(rmix, "", unreal.MaterialProperty.MP_ROUGHNESS)
library.recompile_material(marble)
unreal.EditorAssetLibrary.save_loaded_asset(marble)
log("marble: " + MARBLE)

# --------------------------------------------------------------- stylobate
style = SV.create_mesh().handle
SV.append_revolve_polygon(style, tf(), [v2(0, 0), v2(16 * V, 0), v2(16 * V, 0.6 * V),
                                        v2(15.2 * V, V), v2(0, V)], 0.0, 96, 360.0, 0)
do("stylo", style is not None)
publish(style, STYLO, "ConvexHulls", 4)

# ------------------------------------------------------------------- ring
ring = SV.create_mesh().handle
SV.append_revolve_polygon(ring, tf(), [v2(14 * V, 0), v2(16 * V, 0), v2(16 * V, V),
                                       v2(15.2 * V, 2 * V), v2(14 * V, 2 * V), v2(14 * V, 0)],
                          0.0, 96, 360.0, 0)
publish(ring, RING, "ConvexHulls", 6)

# ------------------------------------------------------------------- dome
dome = SV.create_mesh().handle
SV.append_revolve_polygon(dome, tf(), [v2(14 * V, 0), v2(16 * V, 0), v2(16 * V, 0.8 * V),
                                       v2(15 * V, V), v2(14 * V, V), v2(14 * V, 0)],
                          0.0, 96, 360.0, 0)
dome_profile = [v2(0, V), v2(14 * V, V)]
for k in range(1, 19):
    a = math.pi * k / 36.0
    dome_profile.append(v2(14 * V * math.sin(a), V + 14 * V * math.cos(a)))
dome_profile.append(v2(0, 15 * V))
SV.append_revolve_polygon(dome, tf(), dome_profile, 0.0, 96, 360.0, 0)
SV.append_sphere(dome, tf(0, 0, 15 * V), V, 32, 16, "Center", 0)
try:
    SV.self_union(dome, True, True)
except TypeError:
    SV.self_union(dome)
info = SV.get_mesh_info(dome)
log("dome tris=%s comps=%s open=%s h=%.0f r=%.0f" % (info.triangle_count, info.connected_components,
                                                     info.open_border_edges,
                                                     info.bounds_max.z - info.bounds_min.z,
                                                     info.bounds_max.x))
publish(dome, DOME, "ConvexHulls", 8)

# ------------------------------------------------------------------ place
placed = 0
if getattr(SV.spawn_static_mesh_actor(STYLO, tf(ORIGIN[0], ORIGIN[1], 0.0), "Pavilion_Stylobate"), "success", False):
    placed += 1
for k in range(8):
    a = 2 * math.pi * k / 8.0
    x = ORIGIN[0] + 12 * V * math.cos(a)
    y = ORIGIN[1] + 12 * V * math.sin(a)
    label = "Pavilion_Column_%02d" % (k + 1)
    if getattr(SV.spawn_static_mesh_actor(COLUMN, tf(x, y, V), label), "success", False):
        placed += 1
        actor = next((q for q in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
                      if q.get_actor_label() == label), None)
        if actor and marble:
            actor.static_mesh_component.set_material(0, marble)
if getattr(SV.spawn_static_mesh_actor(RING, tf(ORIGIN[0], ORIGIN[1], 14 * V), "Pavilion_EntablatureRing"),
           "success", False):
    placed += 1
if getattr(SV.spawn_static_mesh_actor(DOME, tf(ORIGIN[0], ORIGIN[1], 16 * V), "Pavilion_Dome"), "success", False):
    placed += 1
log("placed %d pavilion actors" % placed)
try:
    saved = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception:
    saved = unreal.EditorLevelLibrary.save_current_level()
log("level saved: %s" % saved)
bad = [e for e in LOG if e[1] is False]
log("steps=%d failed=%d" % (len(LOG), len(bad)))
log("RESULT: " + ("PASS" if not bad else "CHECK"))
