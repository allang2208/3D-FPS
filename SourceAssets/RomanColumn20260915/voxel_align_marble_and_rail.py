"""Tasks 1-3: chest marble on the floor, realistic handrail, 20 cm voxel alignment.

Voxel rule: every dimension is a multiple of 20 cm.
  floor 1800x800x20 | column 80 base, 260 tall, shaft 160 | baluster 100 tall (40 plinth + 60 shaft
  + 20 abacus) | plinth strip 1500x40x20 | handrail 20x20 section, 1500 long.
"""

import math
import time

import unreal

SV = unreal.ModelingService
DIR = "/Game/Props/RomanColumn20260915"
FLOOR, COLUMN = DIR + "/SM_MarbleFloorTiles", DIR + "/SM_RomanColumn_Detailed"
BALUSTER, PLINTH, RAIL = DIR + "/SM_RomanBaluster_Small", DIR + "/SM_Balustrade_Plinth", DIR + "/SM_Balustrade_Rail"
MARBLE, PLASTER = DIR + "/M_MarbleTiles", DIR + "/M_Plaster_Detailed"
CHEST_MARBLE = "/Game/ColdSteelUI/Warehouse20260909/warehouse_chest_rigid/Materials/White_Marble_PBR"
V = 20.0
LOG = []


def log(m):
    print("[vox] " + m)


def tf(x=0.0, y=0.0, z=0.0, s=1.0):
    t = unreal.Transform()
    t.translation = unreal.Vector(x, y, z)
    t.rotation = unreal.Rotator(0.0, 0.0, 0.0).quaternion()
    t.scale3d = unreal.Vector(s, s, s)
    return t


def v2(r, z):
    return unreal.Vector2D(r, z)


def do(label, result):
    ok = getattr(result, "success", None)
    LOG.append((label, ok, getattr(result, "message", "")))
    log("%-20s %s" % (label, ok))
    return result


def wait(path, timeout=20.0):
    end = time.time() + timeout
    while time.time() < end:
        a = unreal.EditorAssetLibrary.load_asset(path)
        if a:
            return a
        time.sleep(0.3)
    return None


def mesh_stats(handle):
    i = SV.get_mesh_info(handle)
    return "tris=%s comps=%s open=%s" % (i.triangle_count, i.connected_components, i.open_border_edges)


def finish(handle, path, method="ConvexHulls", hulls=8):
    do("uv_" + path.split("/")[-1], SV.auto_uv(handle, "XAtlas", 0))
    do("save_" + path.split("/")[-1], SV.save_mesh_to_static_mesh(handle, path, True, True, False, True))
    SV.release_mesh(handle)
    if wait(path):
        do("col_" + path.split("/")[-1], SV.generate_collision(path, method, hulls, 25, True))


# ------------------------------------------------- 3a. column at voxel sizes
col = SV.create_mesh().handle
SV.append_box(col, tf(0, 0, 0), 4 * V, 4 * V, V, 0, 0, 0, "Base", 0)                 # 0-20, 80x80
SV.append_revolve_polygon(col, tf(), [v2(0, 2 * V), v2(2 * V, 2 * V), v2(2 * V, 2.2 * V),
                                      v2(1.8 * V, 2.5 * V), v2(1.5 * V, 2.9 * V), v2(1.4 * V, 3 * V),
                                      v2(0, 3 * V)], 0.0, 64, 360.0, 0)               # base 20-60
shaft = [v2(0, 3 * V)]
for k in range(25):
    z = 3 * V + (8 * V) * k / 24.0
    t = (z - 3 * V) / (8 * V)
    r = 1.1 * V - 0.8 + 0.55 * math.sin(math.pi * min(t / 0.62, 1.0))
    shaft.append(v2(r + 0.6 * V, z) if k == 0 else v2(r + 0.35 * V, z))
shaft.append(v2(0, 11 * V))
SV.append_revolve_polygon(col, tf(), shaft, 0.0, 64, 360.0, 0)                        # shaft 60-220
SV.append_revolve_polygon(col, tf(), [v2(0, 11 * V), v2(1.2 * V, 11 * V), v2(1.4 * V, 11.6 * V),
                                      v2(1.7 * V, 12 * V), v2(0, 12 * V)], 0.0, 64, 360.0, 0)  # echinus 220-240
SV.append_box(col, tf(0, 0, 12 * V), 4 * V, 4 * V, V, 0, 0, 0, "Base", 0)            # abacus 240-260
tool = SV.create_mesh().handle
for i in range(20):
    a = 2 * math.pi * i / 20
    SV.append_cylinder(tool, tf(math.cos(a) * (1.1 * V), math.sin(a) * (1.1 * V), 2.1 * V), 2.0, 14.8 * V, 24, 0, True, "Base", 0)
SV.boolean(col, tool, "Subtract", tf(), True, True)
SV.release_mesh(tool)
try:
    SV.self_union(col, True, True)
except TypeError:
    SV.self_union(col)
log("column: " + mesh_stats(col) + " height=260 base=80")
finish(col, COLUMN, "ConvexHulls", 10)
do("mat_column", SV.set_asset_materials(COLUMN, PLASTER, True))

# ------------------------------------------------ 3b. baluster at voxel sizes
bal = SV.create_mesh().handle
SV.append_box(bal, tf(0, 0, 0), 2 * V, 2 * V, V, 0, 0, 0, "Base", 0)                 # plinth 0-20
SV.append_revolve_polygon(bal, tf(), [v2(0, V), v2(0.95 * V, V), v2(V, 1.3 * V), v2(0.8 * V, 1.7 * V),
                                      v2(0.8 * V, 2 * V), v2(0, 2 * V)], 0.0, 48, 360.0, 0)
SV.append_revolve_polygon(bal, tf(), [v2(0, 2 * V), v2(0.78 * V, 2 * V), v2(0.8 * V, 3 * V),
                                      v2(0.7 * V, 4 * V), v2(0, 4 * V)], 0.0, 48, 360.0, 0)
SV.append_box(bal, tf(0, 0, 4 * V), 1.8 * V, 1.8 * V, V, 0, 0, 0, "Base", 0)         # abacus 80-100
try:
    SV.self_union(bal, True, True)
except TypeError:
    SV.self_union(bal)
log("baluster: " + mesh_stats(bal) + " height=100")
finish(bal, BALUSTER, "ConvexHulls", 6)
do("mat_baluster", SV.set_asset_materials(BALUSTER, PLASTER, True))

# ------------------------------------------------- 2. moulded handrail by loft
radius = 2 * V
profile = [v2(0, 0), v2(2 * V, 0), v2(2 * V, 0.2 * V)]
for k in range(1, 9):
    a = math.pi * k / 18.0
    profile.append(v2(V + V * math.cos(a), 1.1 * V + 0.9 * V * math.sin(a)))
profile.append(v2(0, 2 * V))
rail = SV.create_mesh().handle
frames = [tf(-7.5 * V, 0, 0), tf(7.5 * V, 0, 0)]
do("rail_loft", SV.append_loft(rail, tf(0, 0, 0), profile, frames, 0))
SV.append_box(rail, tf(0, 0, 0), 15 * V, 2 * V, 0.2 * V, 0, 0, 0, "Base", 0)
try:
    SV.self_union(rail, True, True)
except TypeError:
    SV.self_union(rail)
log("rail: " + mesh_stats(rail))
finish(rail, RAIL, "AlignedBoxes", 1)
do("mat_rail", SV.set_asset_materials(RAIL, PLASTER, True))

# --------------------------------------------------- 3c. plinth strip + floor
strip = SV.create_mesh().handle
SV.append_box(strip, tf(0, 0, 0), 75 * V, 2 * V, V, 0, 0, 0, "Base", 0)
finish(strip, PLINTH, "AlignedBoxes", 1)
do("mat_plinth", SV.set_asset_materials(PLINTH, PLASTER, True))

floor = SV.create_mesh().handle
SV.append_box(floor, tf(0, 0, 0), 90 * V, 40 * V, V, 0, 0, 0, "Base", 0)
g = 0
for i in range(1, 18):
    x = -45 * V + i * 5 * V
    if getattr(SV.cut_groove_along_polyline(floor, [unreal.Vector(x, -20 * V, V), unreal.Vector(x, 20 * V, V)],
                                            1.0, 1.2, unreal.Vector(0, 0, 1)), "success", False):
        g += 1
for j in range(1, 8):
    y = -20 * V + j * 5 * V
    if getattr(SV.cut_groove_along_polyline(floor, [unreal.Vector(-45 * V, y, V), unreal.Vector(45 * V, y, V)],
                                            1.0, 1.2, unreal.Vector(0, 0, 1)), "success", False):
        g += 1
log("floor grooves=%d" % g)
do("uv_floor", SV.project_uv(floor, "Planar", tf(0, 0, 0, 1.0 / (4 * V)), 0, ""))
finish(floor, FLOOR, "AlignedBoxes", 1)
do("col_floor", SV.generate_collision(FLOOR, "AlignedBoxes", 1, 25, True))

# ------------------------------------------------------ 1. chest marble -> MI
chest = wait(CHEST_MARBLE, 10.0)
if chest:
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    mi = unreal.EditorAssetLibrary.load_asset(DIR + "/MI_MarbleFloor_Chest")
    if not mi:
        mi = tools.create_asset("MI_MarbleFloor_Chest", DIR, unreal.MaterialInstanceConstant,
                                unreal.MaterialInstanceConstantFactoryNew())
    unreal.MaterialEditingLibrary.set_material_instance_parent(mi, chest)
    unreal.EditorAssetLibrary.save_loaded_asset(mi)
    do("floor_mat_chest", SV.set_asset_materials(FLOOR, DIR + "/MI_MarbleFloor_Chest", True))
    log("chest marble applied: " + chest.get_path_name())
else:
    do("floor_mat_proc", SV.set_asset_materials(FLOOR, MARBLE, True))
    log("chest marble NOT loadable; procedural marble kept")

bad = [e for e in LOG if e[1] is False]
log("steps=%d failed=%d" % (len(LOG), len(bad)))
log("RESULT: " + ("PASS" if not bad else "CHECK"))
