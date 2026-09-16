"""Restore the original stacked-moulding column, then keep the grid alignment and detail passes.

Original (v1) look: plinth box + torus + cone + cylinder shaft + 20 flutes + torus + cone + abacus.
Kept from later work: every band on the 20 cm grid, 260 tall / 80 base, single manifold, bevel,
noise displacement. Material switches to the parametric stone so the voxel-pipeline material's
missing collection parameters can no longer blank parts of the mesh.
"""

import math
import time

import unreal

SV = unreal.ModelingService
D = "/Game/Props/RomanColumn20260915"
COLUMN, SEG = D + "/SM_RomanColumn_Detailed", D + "/SM_BalustradeSegment_20"
STONE = D + "/M_RomanStone_V2"
PLASTER = D + "/M_Plaster_Detailed"
VEIN, DETAIL = D + "/T_Stone_V2_Noise", D + "/T_Stone_V2_Detail"
V = 20.0
LOG = []


def log(m):
    print("[v1] " + m)


def tf(x=0.0, y=0.0, z=0.0):
    t = unreal.Transform()
    t.translation = unreal.Vector(x, y, z)
    t.rotation = unreal.Rotator(0.0, 0.0, 0.0).quaternion()
    t.scale3d = unreal.Vector(1.0, 1.0, 1.0)
    return t


def do(label, result):
    ok = getattr(result, "success", None)
    LOG.append((label, ok))
    log("%-16s %s" % (label, ok))
    return result


def wait(p, t=15.0):
    end = time.time() + t
    while time.time() < end:
        a = unreal.EditorAssetLibrary.load_asset(p)
        if a:
            return a
        time.sleep(0.3)
    return None


# ------------------------------------------------------------------ stone material
do("noise", SV.create_noise_texture(VEIN, 1024, 1024, 9.0, 5, 0.58, 5150, True))
do("detail", SV.create_noise_texture(DETAIL, 1024, 1024, 34.0, 3, 0.45, 5151, True))
vein, detail = wait(VEIN), wait(DETAIL)
tools = unreal.AssetToolsHelpers.get_asset_tools()
L = unreal.MaterialEditingLibrary
stone = unreal.EditorAssetLibrary.load_asset(STONE)
if not stone:
    stone = tools.create_asset("M_RomanStone_V2", D, unreal.Material, unreal.MaterialFactoryNew())
L.delete_all_material_expressions(stone)
body = L.create_material_expression(stone, unreal.MaterialExpressionVectorParameter, -900, -300)
body.set_editor_property("parameter_name", "StoneBody")
body.set_editor_property("default_value", unreal.LinearColor(0.62, 0.61, 0.58, 1.0))
dirt = L.create_material_expression(stone, unreal.MaterialExpressionVectorParameter, -900, -120)
dirt.set_editor_property("parameter_name", "StoneDirt")
dirt.set_editor_property("default_value", unreal.LinearColor(0.40, 0.39, 0.36, 1.0))
n1 = L.create_material_expression(stone, unreal.MaterialExpressionTextureSampleParameter2D, -900, 60)
n1.set_editor_property("parameter_name", "StoneNoise")
n1.set_editor_property("texture", vein)
n2 = L.create_material_expression(stone, unreal.MaterialExpressionTextureSampleParameter2D, -900, 260)
n2.set_editor_property("parameter_name", "StoneDetail")
n2.set_editor_property("texture", detail)
mix = L.create_material_expression(stone, unreal.MaterialExpressionLinearInterpolate, -600, -220)
r1 = L.create_material_expression(stone, unreal.MaterialExpressionScalarParameter, -600, 120)
r1.set_editor_property("parameter_name", "StoneRoughnessMin")
r1.set_editor_property("default_value", 0.55)
r2 = L.create_material_expression(stone, unreal.MaterialExpressionScalarParameter, -600, 260)
r2.set_editor_property("parameter_name", "StoneRoughnessMax")
r2.set_editor_property("default_value", 0.78)
rmix = L.create_material_expression(stone, unreal.MaterialExpressionLinearInterpolate, -340, 200)
L.connect_material_expressions(n1, "R", mix, "Alpha")
L.connect_material_expressions(body, "", mix, "A")
L.connect_material_expressions(dirt, "", mix, "B")
L.connect_material_expressions(n2, "R", rmix, "Alpha")
L.connect_material_expressions(r1, "", rmix, "A")
L.connect_material_expressions(r2, "", rmix, "B")
L.connect_material_property(mix, "", unreal.MaterialProperty.MP_BASE_COLOR)
L.connect_material_property(rmix, "", unreal.MaterialProperty.MP_ROUGHNESS)
L.recompile_material(stone)
unreal.EditorAssetLibrary.save_loaded_asset(stone)
log("stone material: " + STONE)

# ------------------------------------------------------------ column, v1 look
col = SV.create_mesh().handle
SV.append_box(col, tf(0, 0, 0), 4 * V, 4 * V, V, 0, 0, 0, "Base", 0)                     # 0-20 plinth
SV.append_cylinder(col, tf(0, 0, V), 1.9 * V, 0.6 * V, 64, 0, True, "Base", 0)            # 20-32
SV.append_torus(col, tf(0, 0, 1.6 * V), 1.7 * V, 0.4 * V, 48, 12, "Base", 0)              # torus 32-48
SV.append_cone(col, tf(0, 0, 2.4 * V), 1.7 * V, 1.15 * V, 0.6 * V, 64, 2, True, "Base", 0)  # 48-60
SV.append_cylinder(col, tf(0, 0, 3 * V), 1.15 * V, 8 * V, 64, 8, True, "Base", 0)         # 60-220 shaft
SV.append_torus(col, tf(0, 0, 10.9 * V), 1.15 * V, 0.25 * V, 48, 10, "Base", 0)           # astragal
SV.append_cone(col, tf(0, 0, 11 * V), 1.15 * V, 1.8 * V, V, 64, 3, True, "Base", 0)       # 220-240 echinus
SV.append_box(col, tf(0, 0, 12 * V), 4 * V, 4 * V, V, 0, 0, 0, "Base", 0)                 # 240-260 abacus

# 20 round flutes, exactly the shaft span 60-220
tool = SV.create_mesh().handle
for i in range(20):
    a = 2 * math.pi * i / 20
    SV.append_cylinder(tool, tf(math.cos(a) * 1.15 * V, math.sin(a) * 1.15 * V, 3 * V),
                       2.2, 8 * V, 24, 0, True, "Base", 0)
SV.boolean(col, tool, "Subtract", tf(), True, True)
SV.release_mesh(tool)

try:
    SV.compute_polygroups(col, "Angle", 24.0, 2)
    do("bevel", SV.bevel_polygroups(col, 0.15, 1, 1.0))
except Exception as exc:  # noqa: BLE001
    log("bevel skipped: %s" % exc)

do("uv", SV.auto_uv(col, "XAtlas", 0))
do("displace", SV.displace_from_texture(col, "", DETAIL + "." + DETAIL.split("/")[-1], 0.10, 0))
info = SV.get_mesh_info(col)
log("column h=%.0f base=%.0f tris=%s comps=%s open=%s" % (
    info.bounds_max.z - info.bounds_min.z, info.bounds_max.x - info.bounds_min.x,
    info.triangle_count, info.connected_components, info.open_border_edges))
do("save", SV.save_mesh_to_static_mesh(col, COLUMN, True, True, False, True))
SV.release_mesh(col)

# ------------------------------------------------------------------ apply stone
for path, hulls in ((COLUMN, 10), (SEG, 6)):
    if wait(path):
        do("collision", SV.generate_collision(path, "ConvexHulls", hulls, 25, True))
        do("material", SV.set_asset_materials(path, STONE, True))

bad = [e for e in LOG if e[1] is False]
log("steps=%d failed=%d" % (len(LOG), len(bad)))
log("RESULT: " + ("PASS" if not bad else "CHECK"))
