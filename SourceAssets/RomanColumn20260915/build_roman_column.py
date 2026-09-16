"""Build a Roman column (多立克式简化) with a plaster material, in-editor via Vibe3D.

Run through the Python remote-execution channel:
    python Tools/AssetPipeline/ue_python_exec.py --script SourceAssets/RomanColumn20260915/build_roman_column.py

Units are centimetres. The column is built from Vibe3D's session-mesh operators
(unreal.ModelingService), unwrapped with XAtlas, saved as a StaticMesh, given
convex collision, and assigned a parameterised plaster material.
"""

import unreal

SV = unreal.ModelingService
ASSET_DIR = "/Game/Props/RomanColumn20260915"
MESH_PATH = ASSET_DIR + "/SM_RomanColumn"
MAT_PATH = ASSET_DIR + "/M_Plaster"

RESULTS = []


def log(message):
    print("[column] " + message)


def transform_at(x, y, z, yaw=0.0):
    t = unreal.Transform()
    t.translation = unreal.Vector(x, y, z)
    t.rotation = unreal.Rotator(0.0, 0.0, yaw).quaternion()
    t.scale3d = unreal.Vector(1.0, 1.0, 1.0)
    return t


def step(label, result):
    success = getattr(result, "success", None)
    message = getattr(result, "message", "")
    # release_mesh returns void; a missing "success" field is not a failure.
    ok = success is True or (success is None and not message)
    RESULTS.append((label, ok, message))
    log("%-28s success=%s %s" % (label, success, message))
    return result


# ---------------------------------------------------------------- geometry

plinth_w = 76.0
base_r = 32.0
shaft_r = 22.0
shaft_h = 200.0
shaft_z = 30.0
collar_h = 6.0
capital_z = shaft_z + shaft_h
flutes = 20

created = step("create_mesh", SV.create_mesh())
mesh = created.handle

# Base: plinth, collar, torus, scotia transition.
step("plinth", SV.append_box(mesh, transform_at(0, 0, 0), plinth_w, plinth_w, 10.0, 0, 0, 0, "Base", 0))
step("collar", SV.append_cylinder(mesh, transform_at(0, 0, 10.0), base_r, collar_h, 64, 0, True, "Base", 0))
step("base_torus", SV.append_torus(mesh, transform_at(0, 0, 16.0), base_r - 2.0, 4.0, 48, 12, "Base", 0))
step("scotia", SV.append_cone(mesh, transform_at(0, 0, 20.0), base_r - 2.0, shaft_r + 1.0, 10.0, 64, 1, True, "Base", 0))

# Shaft.
step("shaft", SV.append_cylinder(mesh, transform_at(0, 0, shaft_z), shaft_r, shaft_h, 64, 1, True, "Base", 0))

# Flutes: vertical grooves cut around the shaft.
import math

groove_failures = 0
for index in range(flutes):
    angle = (2.0 * math.pi / flutes) * index
    ux, uy = math.cos(angle), math.sin(angle)
    bottom = unreal.Vector(ux * shaft_r, uy * shaft_r, shaft_z + 2.0)
    top = unreal.Vector(ux * shaft_r, uy * shaft_r, shaft_z + shaft_h - 2.0)
    result = SV.cut_groove_along_polyline(mesh, [bottom, top], 3.6, 1.1, unreal.Vector(ux, uy, 0.0))
    if not getattr(result, "success", False):
        groove_failures += 1
log("flutes cut=%d failures=%d" % (flutes - groove_failures, groove_failures))

# Capital: astragal, echinus, abacus.
step("capital_astragal", SV.append_torus(mesh, transform_at(0, 0, capital_z), shaft_r + 1.0, 2.5, 48, 10, "Base", 0))
step("echinus", SV.append_cone(mesh, transform_at(0, 0, capital_z + 4.0), shaft_r + 1.0, 31.0, 14.0, 64, 2, True, "Base", 0))
step("abacus", SV.append_box(mesh, transform_at(0, 0, capital_z + 18.0), 64.0, 64.0, 9.0, 0, 0, 0, "Base", 0))

log("mesh info: " + str(SV.get_mesh_info(mesh)))

# ------------------------------------------------------------------- UV

step("auto_uv", SV.auto_uv(mesh, "XAtlas", 0))
log("uv stats: " + str(SV.get_uv_stats(mesh, 0, 512)))

# ------------------------------------------------------- save + collision

unreal.EditorAssetLibrary.make_directory(ASSET_DIR)
step("save_mesh", SV.save_mesh_to_static_mesh(mesh, MESH_PATH, True, True, False, True))
step("collision", SV.generate_collision(MESH_PATH, "ConvexHulls", 8, 25, True))

# ---------------------------------------------------------------- plaster

tools = unreal.AssetToolsHelpers.get_asset_tools()
material = unreal.EditorAssetLibrary.load_asset(MAT_PATH)
if not material:
    material = tools.create_asset("M_Plaster", ASSET_DIR, unreal.Material, unreal.MaterialFactoryNew())
library = unreal.MaterialEditingLibrary
library.delete_all_material_expressions(material)

color = library.create_material_expression(material, unreal.MaterialExpressionVectorParameter, -500, -250)
color.set_editor_property("parameter_name", "PlasterColor")
color.set_editor_property("default_value", unreal.LinearColor(0.86, 0.84, 0.80, 1.0))

roughness = library.create_material_expression(material, unreal.MaterialExpressionScalarParameter, -500, -60)
roughness.set_editor_property("parameter_name", "PlasterRoughness")
roughness.set_editor_property("default_value", 0.76)

metallic = library.create_material_expression(material, unreal.MaterialExpressionScalarParameter, -500, 120)
metallic.set_editor_property("parameter_name", "PlasterMetallic")
metallic.set_editor_property("default_value", 0.0)

library.connect_material_property(color, "", unreal.MaterialProperty.MP_BASE_COLOR)
library.connect_material_property(roughness, "", unreal.MaterialProperty.MP_ROUGHNESS)
library.connect_material_property(metallic, "", unreal.MaterialProperty.MP_METALLIC)
library.recompile_material(material)
unreal.EditorAssetLibrary.save_loaded_asset(material)
log("material saved: " + MAT_PATH)

step("assign_material", SV.set_asset_materials(MESH_PATH, MAT_PATH, True))

# --------------------------------------------------------------- cleanup

step("release_mesh", SV.release_mesh(mesh))

log("=== summary ===")
for label, success, message in RESULTS:
    log("  %-28s %s" % (label, "OK" if success else "FAILED %s" % message))
log("RESULT: " + ("PASS" if all(entry[1] for entry in RESULTS) and groove_failures == 0 else "CHECK"))
