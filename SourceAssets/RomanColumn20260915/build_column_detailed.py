"""Detailed Roman column: lathe profile with entasis, round flutes, micro relief, chamfers.

Run: python Tools/AssetPipeline/ue_python_exec.py --script <this file>

Conventions learned from probing the service:
  * append_revolve_polygon: final radius = radius + profile.X, so pass radius=0 and use cm in profile X.
  * append_* take unreal.Transform with translation / rotation / scale3d.
Units are centimetres.
"""

import math

import unreal

SV = unreal.ModelingService
DIR = "/Game/Props/RomanColumn20260915"
MESH = DIR + "/SM_RomanColumn_Detailed"
MAT = DIR + "/M_Plaster_Detailed"
NOISE = DIR + "/T_PlasterNoise"

LOG = []


def log(message):
    print("[col2] " + message)


def tf(x=0.0, y=0.0, z=0.0):
    t = unreal.Transform()
    t.translation = unreal.Vector(x, y, z)
    t.rotation = unreal.Rotator(0.0, 0.0, 0.0).quaternion()
    t.scale3d = unreal.Vector(1.0, 1.0, 1.0)
    return t


def v2(radius, height):
    return unreal.Vector2D(radius, height)


def do(label, result):
    ok = getattr(result, "success", None)
    msg = getattr(result, "message", "")
    LOG.append((label, ok, msg))
    log("%-22s %s %s" % (label, ok, msg))
    return result


# --------------------------------------------------------------- shaft profile
# Doric entasis: slight swell around the lower third, tapering to the top.
shaft_bottom_z = 30.0
shaft_height = 200.0
shaft_top_z = shaft_bottom_z + shaft_height
r_bottom, r_top, r_swell = 21.4, 20.6, 22.05


def shaft_radius(z):
    t = (z - shaft_bottom_z) / shaft_height
    linear = r_bottom + (r_top - r_bottom) * t
    swell = (r_swell - max(r_bottom, r_top)) * math.sin(math.pi * min(t / 0.62, 1.0))
    return linear + max(0.0, swell)


shaft_profile = [v2(shaft_radius(z), z) for z in
                 [shaft_bottom_z + shaft_height * i / 24.0 for i in range(25)]]

base_profile = [
    v2(38.0, 12.0), v2(38.0, 13.5), v2(34.5, 15.0), v2(33.6, 16.6),
    v2(33.0, 17.0), v2(31.4, 18.6), v2(28.8, 20.2), v2(26.6, 21.8),
    v2(25.6, 23.0), v2(27.2, 23.9), v2(28.2, 25.1), v2(28.2, 26.9),
    v2(27.2, 28.1), v2(25.6, 29.0), v2(23.4, 29.6), v2(22.2, 30.0),
]

capital_profile = [
    v2(22.2, 230.0), v2(21.6, 231.2), v2(20.4, 232.6), v2(20.2, 234.0),
    v2(20.8, 236.0), v2(22.4, 238.0), v2(24.6, 241.0), v2(27.2, 244.0),
    v2(29.6, 247.0), v2(31.2, 249.5), v2(32.0, 251.0), v2(32.0, 252.0),
]

# ------------------------------------------------------------------- assemble
mesh = do("create_mesh", SV.create_mesh()).handle
do("plinth", SV.append_box(mesh, tf(0, 0, 0), 76.0, 76.0, 12.0, 0, 0, 0, "Base", 0))
do("base_revolve", SV.append_revolve_polygon(mesh, tf(), base_profile, 0.0, 64, 360.0, 0))
do("shaft_revolve", SV.append_revolve_polygon(mesh, tf(), shaft_profile, 0.0, 64, 360.0, 0))
do("capital_revolve", SV.append_revolve_polygon(mesh, tf(), capital_profile, 0.0, 64, 360.0, 0))
do("abacus", SV.append_box(mesh, tf(0, 0, 252.0), 66.0, 66.0, 10.0, 0, 0, 0, "Base", 0))
do("abacus_crown", SV.append_box(mesh, tf(0, 0, 262.0), 62.0, 62.0, 3.0, 0, 0, 0, "Base", 0))

# --------------------------------------------------------------------- flutes
flute_tool = SV.create_mesh().handle
flutes = 20
for index in range(flutes):
    angle = 2.0 * math.pi * index / flutes
    radius = 22.5
    do("flute_tool_%d" % index, SV.append_cylinder(
        flute_tool,
        tf(math.cos(angle) * radius, math.sin(angle) * radius, shaft_bottom_z + 1.0),
        2.0, shaft_height - 2.0, 24, 0, True, "Base", 0))
do("flute_boolean", SV.boolean(mesh, flute_tool, "Subtract", tf(), True, True))
SV.release_mesh(flute_tool)

info = SV.get_mesh_info(mesh)
log("after flutes: tris=%s verts=%s bounds=%s..%s" % (
    info.triangle_count, info.vertex_count, info.bounds_min, info.bounds_max))

# -------------------------------------------------------------------- bevels
try:
    do("polygroups", SV.compute_polygroups(mesh, "Angle", 24.0, 2))
    do("bevel", SV.bevel_polygroups(mesh, 0.12, 1, 1.0))
except Exception as exc:  # noqa: BLE001
    log("bevel skipped: %s" % exc)

# ------------------------------------------------------------------------- UV
do("auto_uv", SV.auto_uv(mesh, "XAtlas", 0))
log("uv: " + str(SV.get_uv_stats(mesh, 0, 512)))

# ------------------------------------------------- micro relief from height map
do("noise_texture", SV.create_noise_texture(NOISE, 1024, 1024, 10.0, 4, 0.55, 20260915, True))
do("displace", SV.displace_from_texture(mesh, "", NOISE + "." + NOISE.split("/")[-1], 0.12, 0))

# --------------------------------------------------------------- save + colli
unreal.EditorAssetLibrary.make_directory(DIR)
do("save_mesh", SV.save_mesh_to_static_mesh(mesh, MESH, True, True, False, True))
do("collision", SV.generate_collision(MESH, "ConvexHulls", 10, 25, True))

# ------------------------------------------------------------------- material
tools = unreal.AssetToolsHelpers.get_asset_tools()
material = unreal.EditorAssetLibrary.load_asset(MAT)
if not material:
    material = tools.create_asset("M_Plaster_Detailed", DIR, unreal.Material, unreal.MaterialFactoryNew())
library = unreal.MaterialEditingLibrary
library.delete_all_material_expressions(material)

base_color = library.create_material_expression(material, unreal.MaterialExpressionVectorParameter, -900, -300)
base_color.set_editor_property("parameter_name", "PlasterColor")
base_color.set_editor_property("default_value", unreal.LinearColor(0.88, 0.86, 0.82, 1.0))

dirt_color = library.create_material_expression(material, unreal.MaterialExpressionVectorParameter, -900, -120)
dirt_color.set_editor_property("parameter_name", "PlasterGrime")
dirt_color.set_editor_property("default_value", unreal.LinearColor(0.63, 0.60, 0.55, 1.0))

noise_tex = library.create_material_expression(material, unreal.MaterialExpressionTextureSampleParameter2D, -900, 80)
noise_tex.set_editor_property("parameter_name", "PlasterNoise")
noise_tex.set_editor_property("texture", unreal.EditorAssetLibrary.load_asset(NOISE))

rough_low = library.create_material_expression(material, unreal.MaterialExpressionScalarParameter, -900, 300)
rough_low.set_editor_property("parameter_name", "PlasterRoughnessMin")
rough_low.set_editor_property("default_value", 0.66)

rough_high = library.create_material_expression(material, unreal.MaterialExpressionScalarParameter, -900, 440)
rough_high.set_editor_property("parameter_name", "PlasterRoughnessMax")
rough_high.set_editor_property("default_value", 0.84)

mix_color = library.create_material_expression(material, unreal.MaterialExpressionLinearInterpolate, -600, -220)
mix_rough = library.create_material_expression(material, unreal.MaterialExpressionLinearInterpolate, -600, 360)

library.connect_material_expressions(noise_tex, "R", mix_color, "Alpha")
library.connect_material_expressions(base_color, "", mix_color, "A")
library.connect_material_expressions(dirt_color, "", mix_color, "B")
library.connect_material_expressions(noise_tex, "R", mix_rough, "Alpha")
library.connect_material_expressions(rough_low, "", mix_rough, "A")
library.connect_material_expressions(rough_high, "", mix_rough, "B")

library.connect_material_property(mix_color, "", unreal.MaterialProperty.MP_BASE_COLOR)
library.connect_material_property(mix_rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
library.recompile_material(material)
unreal.EditorAssetLibrary.save_loaded_asset(material)
log("material: " + MAT)

do("assign_material", SV.set_asset_materials(MESH, MAT, True))
SV.release_mesh(mesh)

log("=== summary ===")
bad = [entry for entry in LOG if entry[1] is False]
log("steps=%d failed=%d" % (len(LOG), len(bad)))
for label, ok, msg in bad:
    log("  FAILED %s %s" % (label, msg))
log("RESULT: " + ("PASS" if not bad else "CHECK"))
