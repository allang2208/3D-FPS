"""Retry of the marble floor / balustrade build with two fixes.

1. Floor UVs use planar projection instead of XAtlas (the 18x8 m slab shattered into 18k islands).
2. Every path-based follow-up (collision, materials, spawning) waits until the asset actually
   loads, because a package written in the same script run is not in the asset registry yet.
"""

import time

import unreal

SV = unreal.ModelingService
DIR = "/Game/Props/RomanColumn20260915"
FLOOR = DIR + "/SM_MarbleFloorTiles"
BALUSTER = DIR + "/SM_RomanBaluster_Small"
RAIL = DIR + "/SM_Balustrade_Rail"
MARBLE = DIR + "/M_MarbleTiles"
PLASTER = DIR + "/M_Plaster_Detailed"

LEVEL_X, LEVEL_Y = 600.0, 600.0
LOG = []


def log(message):
    print("[finish] " + message)


def tf(x=0.0, y=0.0, z=0.0):
    t = unreal.Transform()
    t.translation = unreal.Vector(x, y, z)
    t.rotation = unreal.Rotator(0.0, 0.0, 0.0).quaternion()
    t.scale3d = unreal.Vector(1.0, 1.0, 1.0)
    return t


def do(label, result):
    ok = getattr(result, "success", None)
    msg = getattr(result, "message", "")
    LOG.append((label, ok, msg))
    log("%-22s %s %s" % (label, ok, msg))
    return result


def wait_for_asset(path, timeout=25.0):
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    deadline = time.time() + timeout
    attempt = 0
    while time.time() < deadline:
        asset = unreal.EditorAssetLibrary.load_asset(path)
        if asset:
            return asset
        attempt += 1
        if attempt % 4 == 0:
            try:
                registry.scan_paths_synchronous([DIR], True, True)
            except Exception:  # noqa: BLE001
                pass
        time.sleep(0.4)
    return None


# ------------------------------------------------------------ rebuild floor
FLOOR_W, FLOOR_D, FLOOR_H = 1800.0, 800.0, 5.0
GRID = 100.0
floor = SV.create_mesh().handle
SV.append_box(floor, tf(0, 0, 0), FLOOR_W, FLOOR_D, FLOOR_H, 0, 0, 0, "Base", 0)
grooves = 0
x = -FLOOR_W / 2 + GRID
while x < FLOOR_W / 2 - 1.0:
    if getattr(SV.cut_groove_along_polyline(
            floor, [unreal.Vector(x, -FLOOR_D / 2, FLOOR_H), unreal.Vector(x, FLOOR_D / 2, FLOOR_H)],
            1.0, 1.2, unreal.Vector(0.0, 0.0, 1.0)), "success", False):
        grooves += 1
    x += GRID
y = -FLOOR_D / 2 + GRID
while y < FLOOR_D / 2 - 1.0:
    if getattr(SV.cut_groove_along_polyline(
            floor, [unreal.Vector(-FLOOR_W / 2, y, FLOOR_H), unreal.Vector(FLOOR_W / 2, y, FLOOR_H)],
            1.0, 1.2, unreal.Vector(0.0, 0.0, 1.0)), "success", False):
        grooves += 1
    y += GRID
log("grooves=%d" % grooves)

# Planar UV from above: one island, texture tiles across the slab.
do("floor_uv", SV.project_uv(floor, "Planar", tf(0, 0, 0), 0, ""))
info = SV.get_mesh_info(floor)
log("floor: tris=%s closed=%s" % (info.triangle_count, info.is_closed))
log("floor uv: " + str(SV.get_uv_stats(floor, 0, 256)))
do("floor_save", SV.save_mesh_to_static_mesh(floor, FLOOR, True, True, False, True))
SV.release_mesh(floor)

# ------------------------------------------------------------- collision pass
for path, method, hulls, label in ((FLOOR, "AlignedBoxes", 1, "floor_collision"),
                                   (BALUSTER, "ConvexHulls", 6, "baluster_collision"),
                                   (RAIL, "AlignedBoxes", 1, "rail_collision")):
    if wait_for_asset(path):
        do(label, SV.generate_collision(path, method, hulls, 25, True))
    else:
        log("SKIP %s: asset never became loadable" % label)

for path, material, label in ((FLOOR, MARBLE, "floor_material"),
                              (BALUSTER, PLASTER, "baluster_material"),
                              (RAIL, PLASTER, "rail_material")):
    if wait_for_asset(path) and wait_for_asset(material):
        do(label, SV.set_asset_materials(path, material, True))
    else:
        log("SKIP %s: asset/material not loadable" % label)

# ------------------------------------------------------------------- place
placed = []
if wait_for_asset(FLOOR):
    result = SV.spawn_static_mesh_actor(FLOOR, tf(LEVEL_X + 750.0, LEVEL_Y - 50.0, 0.2), "MarbleFloor_Colonnade")
    if getattr(result, "success", False):
        placed.append("MarbleFloor_Colonnade")

fence_y = LEVEL_Y + 330.0
index = 0
x = LEVEL_X
while x <= LEVEL_X + 1500.5:
    label = "Baluster_%02d" % (index + 1)
    if getattr(SV.spawn_static_mesh_actor(BALUSTER, tf(x, fence_y, 0.0), label), "success", False):
        placed.append(label)
    index += 1
    x += 150.0

for suffix, z in (("Bottom", 12.0), ("Top", 80.5)):
    label = "BalustradeRail_%s" % suffix
    if getattr(SV.spawn_static_mesh_actor(RAIL, tf(LEVEL_X + 750.0, fence_y, z), label), "success", False):
        placed.append(label)

log("placed %d actors: %s" % (len(placed), ", ".join(placed[:4]) + ("..." if len(placed) > 4 else "")))
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
