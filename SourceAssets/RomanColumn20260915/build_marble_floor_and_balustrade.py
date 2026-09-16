"""Marble floor tiles + low Roman baluster fence, built with Vibe3D and placed in the home scene.

Marble source: tries the warehouse White_Marble_PBR asset first (it was on disk but absent from
the asset registry, so a synchronous rescan is attempted); otherwise a procedural veined marble
material is generated from Vibe3D noise textures.
"""

import math

import unreal

SV = unreal.ModelingService
DIR = "/Game/Props/RomanColumn20260915"
FLOOR = DIR + "/SM_MarbleFloorTiles"
BALUSTER = DIR + "/SM_RomanBaluster_Small"
RAIL = DIR + "/SM_Balustrade_Rail"
MARBLE = DIR + "/M_MarbleTiles"
PLASTER = DIR + "/M_Plaster_Detailed"
VEIN = DIR + "/T_MarbleVeins"
DETAIL = DIR + "/T_MarbleDetail"

LEVEL_X, LEVEL_Y = 600.0, 600.0
LOG = []


def log(message):
    print("[marble] " + message)


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


def existing_marble():
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    try:
        registry.scan_paths_synchronous(["/Game/ColdSteelUI"], True, True)
    except Exception as exc:  # noqa: BLE001
        log("registry scan failed: %s" % exc)
    for candidate in ("/Game/ColdSteelUI/Warehouse20260909/warehouse_chest_rigid/Materials/White_Marble_PBR",
                      "/Game/ColdSteelUI/Warehouse20260909/RuntimeSurfaces/Surface_White_Marble_PBR"):
        asset = unreal.EditorAssetLibrary.load_asset(candidate)
        if asset:
            log("found existing marble: %s" % candidate)
            return asset
    log("no registered marble asset; using procedural marble")
    return None


# ------------------------------------------------------------- floor tiles
FLOOR_W, FLOOR_D, FLOOR_H = 1800.0, 800.0, 5.0
GRID = 100.0
floor = do("create_floor", SV.create_mesh()).handle
do("slab", SV.append_box(floor, tf(0, 0, 0), FLOOR_W, FLOOR_D, FLOOR_H, 0, 0, 0, "Base", 0))

grooves = 0
x = -FLOOR_W / 2 + GRID
while x < FLOOR_W / 2 - 1.0:
    r = SV.cut_groove_along_polyline(floor, [unreal.Vector(x, -FLOOR_D / 2, FLOOR_H),
                                             unreal.Vector(x, FLOOR_D / 2, FLOOR_H)],
                                     1.0, 1.2, unreal.Vector(0.0, 0.0, 1.0))
    grooves += 1 if getattr(r, "success", False) else 0
    x += GRID
y = -FLOOR_D / 2 + GRID
while y < FLOOR_D / 2 - 1.0:
    r = SV.cut_groove_along_polyline(floor, [unreal.Vector(-FLOOR_W / 2, y, FLOOR_H),
                                             unreal.Vector(FLOOR_W / 2, y, FLOOR_H)],
                                     1.0, 1.2, unreal.Vector(0.0, 0.0, 1.0))
    grooves += 1 if getattr(r, "success", False) else 0
    y += GRID
log("grooves cut: %d" % grooves)
try:
    do("floor_polygroups", SV.compute_polygroups(floor, "Angle", 30.0, 2))
    do("floor_bevel", SV.bevel_polygroups(floor, 0.15, 1, 1.0))
except Exception as exc:  # noqa: BLE001
    log("floor bevel skipped: %s" % exc)
do("floor_uv", SV.auto_uv(floor, "XAtlas", 0))
log("floor uv: " + str(SV.get_uv_stats(floor, 0, 256)))
unreal.EditorAssetLibrary.make_directory(DIR)
do("floor_save", SV.save_mesh_to_static_mesh(floor, FLOOR, True, True, False, True))
do("floor_collision", SV.generate_collision(FLOOR, "AlignedBoxes", 1, 25, True))
SV.release_mesh(floor)

# ---------------------------------------------------------------- baluster
bal = do("create_baluster", SV.create_mesh()).handle
do("b_plinth", SV.append_box(bal, tf(0, 0, 0), 26.0, 26.0, 8.0, 0, 0, 0, "Base", 0))
do("b_base", SV.append_revolve_polygon(bal, tf(), [
    v2(0.0, 7.5), v2(13.0, 7.5), v2(13.0, 9.0), v2(11.0, 10.5), v2(9.5, 12.0),
    v2(9.5, 13.0), v2(0.0, 13.0)] + [v2(0.0, 13.0)], 0.0, 48, 360.0, 0))
do("b_shaft", SV.append_revolve_polygon(bal, tf(), [
    v2(0.0, 12.5), v2(8.6, 12.5), v2(8.8, 25.0), v2(8.9, 40.0), v2(8.6, 55.0),
    v2(8.2, 68.0), v2(8.0, 72.0), v2(0.0, 72.0)], 0.0, 48, 360.0, 0))
do("b_capital", SV.append_revolve_polygon(bal, tf(), [
    v2(0.0, 71.5), v2(8.2, 71.5), v2(9.0, 73.0), v2(11.0, 76.0), v2(12.4, 79.0),
    v2(12.6, 80.0), v2(0.0, 80.0)], 0.0, 48, 360.0, 0))
do("b_abacus", SV.append_box(bal, tf(0, 0, 79.5), 24.0, 24.0, 6.5, 0, 0, 0, "Base", 0))
try:
    do("b_union", SV.self_union(bal, True, True))
except TypeError:
    do("b_union", SV.self_union(bal))
info = SV.get_mesh_info(bal)
log("baluster: closed=%s open_edges=%s components=%s tris=%s" % (
    info.is_closed, info.open_border_edges, info.connected_components, info.triangle_count))
do("b_uv", SV.auto_uv(bal, "XAtlas", 0))
do("b_save", SV.save_mesh_to_static_mesh(bal, BALUSTER, True, True, False, True))
do("b_collision", SV.generate_collision(BALUSTER, "ConvexHulls", 6, 25, True))
SV.release_mesh(bal)

# -------------------------------------------------------------------- rail
rail = do("create_rail", SV.create_mesh()).handle
do("rail_body", SV.append_box(rail, tf(0, 0, 0), 1600.0, 20.0, 8.0, 0, 0, 0, "Base", 0))
do("rail_top", SV.append_box(rail, tf(0, 0, 7.5), 1620.0, 26.0, 5.0, 0, 0, 0, "Base", 0))
try:
    do("rail_union", SV.self_union(rail, True, True))
except TypeError:
    do("rail_union", SV.self_union(rail))
do("rail_uv", SV.auto_uv(rail, "XAtlas", 0))
do("rail_save", SV.save_mesh_to_static_mesh(rail, RAIL, True, True, False, True))
do("rail_collision", SV.generate_collision(RAIL, "AlignedBoxes", 1, 25, True))
SV.release_mesh(rail)

# --------------------------------------------------------------- materials
marble_source = existing_marble()
tools = unreal.AssetToolsHelpers.get_asset_tools()
library = unreal.MaterialEditingLibrary

if not marble_source:
    do("vein_texture", SV.create_noise_texture(VEIN, 1024, 1024, 4.0, 6, 0.62, 771, True))
    do("detail_texture", SV.create_noise_texture(DETAIL, 1024, 1024, 26.0, 3, 0.45, 991, True))
    marble = unreal.EditorAssetLibrary.load_asset(MARBLE)
    if not marble:
        marble = tools.create_asset("M_MarbleTiles", DIR, unreal.Material, unreal.MaterialFactoryNew())
    library.delete_all_material_expressions(marble)
    white = library.create_material_expression(marble, unreal.MaterialExpressionVectorParameter, -1000, -320)
    white.set_editor_property("parameter_name", "MarbleBody")
    white.set_editor_property("default_value", unreal.LinearColor(0.93, 0.92, 0.90, 1.0))
    vein_col = library.create_material_expression(marble, unreal.MaterialExpressionVectorParameter, -1000, -150)
    vein_col.set_editor_property("parameter_name", "MarbleVein")
    vein_col.set_editor_property("default_value", unreal.LinearColor(0.52, 0.53, 0.58, 1.0))
    veins = library.create_material_expression(marble, unreal.MaterialExpressionTextureSampleParameter2D, -1000, 40)
    veins.set_editor_property("parameter_name", "VeinNoise")
    veins.set_editor_property("texture", unreal.EditorAssetLibrary.load_asset(VEIN))
    detail = library.create_material_expression(marble, unreal.MaterialExpressionTextureSampleParameter2D, -1000, 260)
    detail.set_editor_property("parameter_name", "DetailNoise")
    detail.set_editor_property("texture", unreal.EditorAssetLibrary.load_asset(DETAIL))
    mix = library.create_material_expression(marble, unreal.MaterialExpressionLinearInterpolate, -700, -240)
    rough_min = library.create_material_expression(marble, unreal.MaterialExpressionScalarParameter, -700, 120)
    rough_min.set_editor_property("parameter_name", "MarbleRoughnessMin")
    rough_min.set_editor_property("default_value", 0.16)
    rough_max = library.create_material_expression(marble, unreal.MaterialExpressionScalarParameter, -700, 260)
    rough_max.set_editor_property("parameter_name", "MarbleRoughnessMax")
    rough_max.set_editor_property("default_value", 0.34)
    rough_mix = library.create_material_expression(marble, unreal.MaterialExpressionLinearInterpolate, -420, 200)
    library.connect_material_expressions(veins, "R", mix, "Alpha")
    library.connect_material_expressions(white, "", mix, "A")
    library.connect_material_expressions(vein_col, "", mix, "B")
    library.connect_material_expressions(detail, "R", rough_mix, "Alpha")
    library.connect_material_expressions(rough_min, "", rough_mix, "A")
    library.connect_material_expressions(rough_max, "", rough_mix, "B")
    library.connect_material_property(mix, "", unreal.MaterialProperty.MP_BASE_COLOR)
    library.connect_material_property(rough_mix, "", unreal.MaterialProperty.MP_ROUGHNESS)
    library.recompile_material(marble)
    unreal.EditorAssetLibrary.save_loaded_asset(marble)
    log("procedural marble material: " + MARBLE)
else:
    marble = marble_source
    log("reusing existing marble material: " + marble.get_path_name())

do("floor_material", SV.set_asset_materials(FLOOR, marble.get_path_name(), True))
do("baluster_material", SV.set_asset_materials(BALUSTER, PLASTER, True))
do("rail_material", SV.set_asset_materials(RAIL, PLASTER, True))

# ------------------------------------------------------------------ place
placed = []
SV.spawn_static_mesh_actor(FLOOR, tf(LEVEL_X + 750.0, LEVEL_Y - 50.0, 0.2), "MarbleFloor_Colonnade")
placed.append("MarbleFloor_Colonnade")

fence_y = LEVEL_Y + 330.0
spacing = 150.0
index = 0
x = LEVEL_X
while x <= LEVEL_X + 1500.0 + 0.5:
    label = "Baluster_%02d" % (index + 1)
    if getattr(SV.spawn_static_mesh_actor(BALUSTER, tf(x, fence_y, 0.0), label), "success", False):
        placed.append(label)
    index += 1
    x += spacing

for suffix, z in (("Top", 80.5), ("Bottom", 12.0)):
    label = "BalustradeRail_%s" % suffix
    if getattr(SV.spawn_static_mesh_actor(RAIL, tf(LEVEL_X + 750.0, fence_y, z), label), "success", False):
        placed.append(label)

log("placed %d actors" % len(placed))
try:
    saved = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception:
    saved = unreal.EditorLevelLibrary.save_current_level()
log("level saved: %s" % saved)

bad = [entry for entry in LOG if entry[1] is False]
log("steps=%d failed=%d" % (len(LOG), len(bad)))
for label, ok, msg in bad:
    log("  FAILED %s %s" % (label, msg))
log("RESULT: " + ("PASS" if not bad else "CHECK"))
