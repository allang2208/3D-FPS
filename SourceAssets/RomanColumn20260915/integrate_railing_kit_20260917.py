"""Integrate the roman railing kit into the ACTIVE build palette + repair door fields.

Headless (editor must be CLOSED so palette saves land on disk):
    UnrealEditor-Cmd FPSGAME.uproject -run=pythonscript -script=<this> -unattended -nosplash
    -nullrhi -nosound -abslog=SourceAssets/RomanColumn20260915/headless_railing_kit_20260917.log

What it does:
  1. Repairs the 2026-09-17 regression: earlier palette rebuilds copied only 6 of the 9
     FVoxelBuildPrefab fields, stripping actor_class/actor_offset_cm/material from the door
     entries. All nine fields are now copied explicitly for every entry.
  2. Builds three moulded rails (arc cross-section, same profile as the in-game segments) at
     100/200/300 cm: SM_RomanRail_100/_200/_300, voxel-aligned, M_RomanStone_V2.
  3. Registers the kit: rail x3 + balustrade_segment (200x40x160 all-in-one piece).
  4. Self-checks every entry's real mesh bbox against its 20 cm footprint (OK / MISMATCH).
"""

import math
import time

import unreal

SV = unreal.ModelingService
D = "/Game/Props/RomanColumn20260915"
PALETTE = "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"
STONE = D + "/M_RomanStone_V2"
SEGMENT = D + "/SM_BalustradeSegment_20"
V = 20.0
LOG = []

# id, caption, mesh path, footprint cells (x,y,z)
RAILS = [
    ("balustrade_rail_100", "罗马栏杆顶梁 1米", D + "/SM_RomanRail_100", (5, 2, 2)),
    ("balustrade_rail_200", "罗马栏杆顶梁 2米", D + "/SM_RomanRail_200", (10, 2, 2)),
    ("balustrade_rail_300", "罗马栏杆顶梁 3米", D + "/SM_RomanRail_300", (15, 2, 2)),
]
SEGMENT_ENTRY = ("balustrade_segment", "罗马栏杆整体段 2米", SEGMENT, (10, 2, 8))

# door repair table: id -> (class path, group)  [same values as add_door_prefab_entries_20260917.py]
DOORS = {
    "door_wood": ("/Script/FPSGAME.ColdSteelDoor", "wood"),
    "door_stone": ("/Script/FPSGAME.ColdSteelDoor", "stone"),
    "door_marble": ("/Script/FPSGAME.ColdSteelDoor", "marble"),
    "door_physics": ("/Game/DoorSystem/Blueprints/Doors/BP_PhysicsDoor.BP_PhysicsDoor_C", ""),
}


def log(m):
    print("[kit] " + m)


def do(label, result):
    ok = getattr(result, "success", None)
    LOG.append((label, ok))
    log("%-16s %s" % (label, ok))
    return result


def tf(x=0.0, y=0.0, z=0.0):
    t = unreal.Transform()
    t.translation = unreal.Vector(x, y, z)
    t.rotation = unreal.Rotator(0.0, 0.0, 0.0).quaternion()
    t.scale3d = unreal.Vector(1.0, 1.0, 1.0)
    return t


def v2(r, z):
    return unreal.Vector2D(r, z)


def wait(path, timeout=25.0):
    end = time.time() + timeout
    while time.time() < end:
        a = unreal.EditorAssetLibrary.load_asset(path)
        if a:
            return a
        time.sleep(0.3)
    return None


def dims_of(path):
    m = unreal.EditorAssetLibrary.load_asset(path)
    if not m:
        return None
    e = m.get_bounds().box_extent
    return (round(e.x * 2, 1), round(e.y * 2, 1), round(e.z * 2, 1))


# ------------------------------------------------- 1. build the three moulded rails
# EXACT cross-section of SM_BalustradeSegment_20's moulded rail (the in-game look):
# 40 cm base, right lip, arc crest, flat left ledge. Centered on y so the bbox is 40 wide.
profile = [v2(-V, 0.0), v2(V, 0.0), v2(V, 0.3 * V)]
for k in range(1, 9):
    a = math.pi * k / 18.0
    profile.append(v2(V * math.cos(a), 0.7 * V + 1.3 * V * math.sin(a)))
profile.append(v2(-V, 2 * V))

for rail_id, _caption, path, (cx, cy, cz) in RAILS:
    if unreal.EditorAssetLibrary.load_asset(path):
        log("%s already on disk, skip build" % path.split("/")[-1])
        continue
    half = cx * V / 2.0
    rail = SV.create_mesh().handle
    do("loft_" + str(cx), SV.append_loft(rail, tf(0, 0, 0), profile,
                                         [tf(-half, 0, 0), tf(half, 0, 0)], 0))
    SV.append_box(rail, tf(0, 0, 0), cx * V, 2 * V, 0.4 * V, 0, 0, 0, "Base", 0)
    try:
        SV.self_union(rail, True, True)
    except TypeError:
        SV.self_union(rail)
    info = SV.get_mesh_info(rail)
    log("rail %d: tris=%s comps=%s open=%s size=(%.1f, %.1f, %.1f)" % (
        cx, info.triangle_count, info.connected_components, info.open_border_edges,
        info.bounds_max.x - info.bounds_min.x, info.bounds_max.y - info.bounds_min.y,
        info.bounds_max.z - info.bounds_min.z))
    do("uv_%d" % cx, SV.auto_uv(rail, "XAtlas", 0))
    do("save_%d" % cx, SV.save_mesh_to_static_mesh(rail, path, True, True, False, True))
    SV.release_mesh(rail)
    if wait(path, 15.0):
        do("col_%d" % cx, SV.generate_collision(path, "AlignedBoxes", 1, 25, True))
        do("mat_%d" % cx, SV.set_asset_materials(path, STONE, True))

# --------------------------------------------------------- 2. rebuild palette entries
pal = wait(PALETTE)
if not pal:
    raise RuntimeError("palette not loadable")

rebuilt = []
for entry in pal.get_editor_property("components") or []:
    copy = unreal.VoxelBuildPrefab()
    # ALL nine fields of FVoxelBuildPrefab — the 2026-09-17 regression was dropping three.
    copy.set_editor_property("id", entry.get_editor_property("id"))
    copy.set_editor_property("display_name", entry.get_editor_property("display_name"))
    copy.set_editor_property("mesh", entry.get_editor_property("mesh"))
    copy.set_editor_property("footprint", entry.get_editor_property("footprint"))
    copy.set_editor_property("surface", entry.get_editor_property("surface"))
    copy.set_editor_property("pivot_offset_cm", entry.get_editor_property("pivot_offset_cm"))
    copy.set_editor_property("actor_class", entry.get_editor_property("actor_class"))
    copy.set_editor_property("actor_offset_cm", entry.get_editor_property("actor_offset_cm"))
    copy.set_editor_property("material", entry.get_editor_property("material"))
    pid = str(copy.get_editor_property("id"))
    if pid in DOORS:
        class_path, group = DOORS[pid]
        actor_class = unreal.load_class(None, class_path)
        if actor_class:
            copy.set_editor_property("actor_class", actor_class)
            copy.set_editor_property("material", unreal.Name(group) if group else unreal.Name("None"))
            log("door repair %s -> class=%s group=%s" % (pid, actor_class.get_name(), group or "None"))
        else:
            log("door repair %s FAILED: class missing %s" % (pid, class_path))
            LOG.append(("door_repair_" + pid, False))
    rebuilt = [e for e in rebuilt if str(e.get_editor_property("id")) != pid]
    rebuilt.append(copy)

# register the kit
stone = wait(STONE, 10.0)
kit = [(pid, cap, mesh_path, cells) for pid, cap, mesh_path, cells in RAILS] + [SEGMENT_ENTRY]
for pid, caption, mesh_path, cells in kit:
    mesh = wait(mesh_path, 10.0)
    if not mesh:
        log("SKIP %s: mesh missing %s" % (pid, mesh_path))
        LOG.append(("kit_" + pid, False))
        continue
    actual = dims_of(mesh_path)
    wanted = tuple(c * 20 for c in cells)
    status = "OK" if all(abs(a - w) < 0.5 for a, w in zip(actual, wanted)) else "MISMATCH"
    log("kit %-22s mesh=%-22s dims=%s wanted=%s %s" % (
        pid, mesh_path.split("/")[-1], actual, wanted, status))
    if status != "OK":
        LOG.append(("kit_dims_" + pid, False))
    entry = unreal.VoxelBuildPrefab()
    entry.set_editor_property("id", pid)
    entry.set_editor_property("display_name", unreal.Text(caption))
    entry.set_editor_property("mesh", mesh)
    entry.set_editor_property("footprint", unreal.IntVector(cells[0], cells[1], cells[2]))
    entry.set_editor_property("surface", stone)
    entry.set_editor_property("pivot_offset_cm", unreal.Vector(0.0, 0.0, 0.0))
    entry.set_editor_property("material", unreal.Name("None"))
    rebuilt = [e for e in rebuilt if str(e.get_editor_property("id")) != pid]
    rebuilt.append(entry)

pal.modify()
pal.set_editor_property("components", rebuilt)
package = unreal.load_package(PALETTE)
log("save_packages=%s" % unreal.EditorLoadingAndSavingUtils.save_packages([package], False))

# ---------------------------------------------------------------------- readback
back = unreal.load_asset(PALETTE)
log("components after: %d" % len(back.get_editor_property("components") or []))
for entry in back.get_editor_property("components") or []:
    mesh = entry.get_editor_property("mesh")
    surface = entry.get_editor_property("surface")
    actor_class = entry.get_editor_property("actor_class")
    extent = mesh.get_bounds().box_extent if mesh else None
    log("  %-22s group=%-7s actor=%-18s surface=%s dims=%s" % (
        str(entry.get_editor_property("id")),
        str(entry.get_editor_property("material")),
        actor_class.get_name() if actor_class else "-",
        surface.get_path_name().split(".")[-1] if surface else "None",
        (round(extent.x * 2, 1), round(extent.y * 2, 1), round(extent.z * 2, 1)) if extent else None))

bad = [e for e in LOG if e[1] is False]
log("steps=%d failed=%d" % (len(LOG), len(bad)))
for label, ok in bad:
    log("  FAILED %s" % label)
log("RESULT: " + ("PASS" if not bad else "CHECK"))
