"""Register the v2 pavilion into the ACTIVE voxel build palette.

Headless (editor must be CLOSED so the palette save lands on disk):
    UnrealEditor-Cmd FPSGAME.uproject -run=pythonscript -script=<this> -unattended -nosplash
    -nullrhi -nosound -abslog=SourceAssets/RomanColumn20260915/integrate_pavilion2_20260917.log

Why a "colonnade" piece exists: the 10 column axes sit on a 360 cm radius, and 360*cos(36k)
lands between grid cells (291.2 cm = 14.56 cells), so a player cannot lay the ring out by
hand on the 20 cm grid. The colonnade prefab carries the columns and the entablature as one
mesh so the ring geometry is exact.

Steps:
  1. Build SM_RomanPavilionColonnade_20 = 10 columns (z 20-280) + entablature + dentils.
  2. Collision, then prove it with in-level rays: through a bay it must MISS so the pavilion
     stays walkable, at a column axis it must HIT, and the cornice top must be solid.
  3. Rewrite the palette: every existing entry copied across all nine FVoxelBuildPrefab
     fields (the 2026-09-17 door regression came from copying only six), doors re-verified,
     then the four pavilion pieces appended.
  4. Self-check each footprint against the real mesh bbox, and read the palette back.
"""

import math
import os
import time

import unreal

SV = unreal.ModelingService
D = "/Game/Props/RomanColumn20260915"
PALETTE = "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"
STONE = D + "/M_RomanStone_V2"
COLUMN = D + "/SM_RomanColumn_Detailed"
COLONNADE = D + "/SM_RomanPavilionColonnade_20"
V = 20.0

R_COL = 360.0
N_COL = 10
COL_H = 260.0          # column height: the entablature's foot, local to this piece
ARCH_H = 80.0          # entablature height
R_ARCH_IN = 320.0
R_ARCH_FACE = 400.0
R_ARCH_OUT = 440.0
N_DENTIL = 72
DENTIL_W, DENTIL_D, DENTIL_H = 16.0, 40.0, 16.0
STEPS = 96
LEVEL = "/Game/GameMaps/DayNight_Lighting"
ORIGIN = (1350.0, -400.0)

# id, caption, mesh path, footprint cells  (footprint must equal the mesh bbox / 20)
PIECES = [
    ("pavilion_base", "罗马凉亭台基 9.6米", D + "/SM_RomanPavilionBase_20", (48, 48, 1)),
    ("pavilion_colonnade", "罗马凉亭柱环 10柱", COLONNADE, (44, 44, 17)),
    ("pavilion_arch", "罗马凉亭额枋环", D + "/SM_RomanPavilionArch_20", (44, 44, 4)),
    ("pavilion_dome", "罗马凉亭穹顶 140凹格", D + "/SM_RomanPavilionDome_20", (40, 40, 20)),
]
DOORS = {
    "door_wood": ("/Script/FPSGAME.ColdSteelDoor", "wood"),
    "door_stone": ("/Script/FPSGAME.ColdSteelDoor", "stone"),
    "door_marble": ("/Script/FPSGAME.ColdSteelDoor", "marble"),
    "door_physics": ("/Game/DoorSystem/Blueprints/Doors/BP_PhysicsDoor.BP_PhysicsDoor_C", ""),
}
LOG = []


def log(m):
    print("[pv2kit] " + m)


def do(label, result):
    ok = getattr(result, "success", None)
    LOG.append((label, ok))
    log("%-20s %s" % (label, ok))
    return result


def tf(x=0.0, y=0.0, z=0.0, pitch=0.0, yaw=0.0, roll=0.0):
    """Python Rotator takes (roll, pitch, yaw) positionally — see build_pavilion2."""
    t = unreal.Transform()
    t.translation = unreal.Vector(x, y, z)
    t.rotation = unreal.Rotator(roll, pitch, yaw).quaternion()
    t.scale3d = unreal.Vector(1.0, 1.0, 1.0)
    return t


def v2(r, z):
    return unreal.Vector2D(r, z)


def wait(path, timeout=20.0):
    end = time.time() + timeout
    while time.time() < end:
        a = unreal.EditorAssetLibrary.load_asset(path)
        if a:
            return a
        time.sleep(0.3)
    return None


def dims_of(path):
    m = wait(path, 10.0)
    if not m:
        return None
    bb = m.get_bounds()
    return (round(bb.box_extent.x * 2, 1), round(bb.box_extent.y * 2, 1), round(bb.box_extent.z * 2, 1))


# ------------------------------------------------- 1. colonnade (10 columns + arch)
col = SV.create_mesh().handle
# local z: 0 = the foot of this piece (the column bases), so the actor's pivot is its base
arch_profile = [
    v2(R_ARCH_IN, COL_H),
    v2(R_ARCH_FACE - 8.0, COL_H), v2(R_ARCH_FACE - 8.0, COL_H + 8.0),
    v2(R_ARCH_FACE - 16.0, COL_H + 12.0), v2(R_ARCH_FACE - 16.0, COL_H + 26.0),
    v2(R_ARCH_FACE - 10.0, COL_H + 26.0), v2(R_ARCH_FACE - 10.0, COL_H + 38.0),
    v2(R_ARCH_FACE - 18.0, COL_H + 38.0), v2(R_ARCH_FACE - 18.0, COL_H + 60.0),
    v2(R_ARCH_FACE - 6.0, COL_H + 60.0), v2(R_ARCH_FACE - 6.0, COL_H + 68.0),
    v2(R_ARCH_FACE + 8.0, COL_H + 72.0), v2(R_ARCH_OUT, COL_H + 76.0),
    v2(R_ARCH_OUT, COL_H + ARCH_H), v2(400.0, COL_H + ARCH_H), v2(R_ARCH_IN, COL_H + ARCH_H),
]
do("arch revolve", SV.append_revolve_polygon(col, tf(), arch_profile, 0.0, STEPS, 360.0, 0))

dentil = SV.create_mesh().handle
SV.append_box(dentil, tf(0.0, 0.0, 0.0), DENTIL_D, DENTIL_W, DENTIL_H, 0, 0, 0, "Center", 0)
dentil_at = []
for k in range(N_DENTIL):
    theta = 360.0 * k / N_DENTIL
    dentil_at.append(tf((R_ARCH_FACE + 4.0) * math.cos(math.radians(theta)),
                        (R_ARCH_FACE + 4.0) * math.sin(math.radians(theta)),
                        COL_H + 64.0, 0.0, theta, 0.0))
SV.append_mesh_at_transforms(col, dentil, dentil_at)
SV.release_mesh(dentil)

loaded = SV.load_mesh_from_static_mesh(COLUMN, 0)
column_handle = getattr(loaded, "handle", None)
if not column_handle:
    raise RuntimeError("cannot load %s" % COLUMN)
log("column source: %d tris" % SV.get_mesh_info(column_handle).triangle_count)
# 10 full-detail columns make this one asset ~270k tris / 11 MB. The rack's columns go
# through a light quadric pass; if that smears the profile too far the full mesh is restored,
# because a wrong-looking column ring is worse than a heavy one.
full_tris = SV.get_mesh_info(column_handle).triangle_count
do("simplify_tol", SV.simplify_to_tolerance(column_handle, 0.05, True))
tris = SV.get_mesh_info(column_handle).triangle_count
if tris < 4000 or tris > 16000:
    log("simplify overshot (%d tris) - restoring the full-detail column" % tris)
    SV.release_mesh(column_handle)
    loaded = SV.load_mesh_from_static_mesh(COLUMN, 0)
    column_handle = getattr(loaded, "handle", None)
    tris = SV.get_mesh_info(column_handle).triangle_count
log("column in rack: %d tris (source %d, %.0f%%)" % (tris, full_tris, 100.0 * tris / full_tris))
# columns at local z 0 so the piece's pivot is its foot (the build script places it at the
# first cell above the base)
column_at = [tf(R_COL * math.cos(2.0 * math.pi * k / N_COL),
                R_COL * math.sin(2.0 * math.pi * k / N_COL), 0.0) for k in range(N_COL)]
do("column ring", SV.append_mesh_at_transforms(col, column_handle, column_at))
SV.release_mesh(column_handle)
info = SV.get_mesh_info(col)
log("colonnade raw: tris=%d comps=%d open=%d size=(%.0f, %.0f, %.0f)" % (
    info.triangle_count, info.connected_components, info.open_border_edges,
    info.bounds_max.x - info.bounds_min.x, info.bounds_max.y - info.bounds_min.y,
    info.bounds_max.z - info.bounds_min.z))
do("uv", SV.auto_uv(col, "XAtlas", 0))
do("save", SV.save_mesh_to_static_mesh(col, COLONNADE, True, True, False, True))
SV.release_mesh(col)
wait(COLONNADE)
do("collision", SV.generate_collision(COLONNADE, "ConvexHulls", 12, 25, True))
do("material", SV.set_asset_materials(COLONNADE, STONE, True))
_bb = wait(COLONNADE).get_bounds()
_lo = _bb.origin.z - _bb.box_extent.z
LOG.append(("pivot_colonnade", abs(_lo) < 0.5))
log("colonnade dims: %s  local z %.1f..%.1f (pivot must be the foot) %s" % (
    dims_of(COLONNADE), _lo, _bb.origin.z + _bb.box_extent.z, "OK" if abs(_lo) < 0.5 else "OFFSET"))

# ------------------------------------------------- 3. prove the collision is walkable
# Runs last on purpose: opening the level in the same process as the palette write is what
# made the earlier save_packages call return False. Nothing here is saved.
def verify_collision():
    sub = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    sub.load_level(LEVEL)
    actor_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    probe = actor_sub.spawn_actor_from_class(
        unreal.StaticMeshActor, unreal.Vector(ORIGIN[0], ORIGIN[1], 0.0), unreal.Rotator(0.0, 0.0, 0.0))
    smc = probe.static_mesh_component
    smc.set_mobility(unreal.ComponentMobility.MOVABLE)
    smc.set_static_mesh(wait(COLONNADE))
    probe.set_actor_label("PavilionProbe_Temp")
    world = unreal.EditorLevelLibrary.get_editor_world()

    def ray(label, start, end, want_hit):
        """start/end are POSITIONS (the second vector is not a direction), channel QUERY2."""
        hit = unreal.SystemLibrary.line_trace_single(
            world, unreal.Vector(*start), unreal.Vector(*end),
            unreal.TraceTypeQuery.TRACE_TYPE_QUERY2, False, [], unreal.DrawDebugTrace.NONE, False)
        got = bool(hit)
        detail = ""
        if hit:
            for attr in ("location", "impact_point", "hit_component"):
                try:
                    value = getattr(hit, attr)
                    detail = "%s=%s" % (attr, (round(value.x, 1), round(value.y, 1), round(value.z, 1))
                                        if attr != "hit_component" else value.get_name())
                    break
                except AttributeError:
                    continue
            if not detail:
                detail = "attrs=%s" % [a for a in dir(hit) if not a.startswith("_")][:6]
        ok = got if want_hit else (not got)
        LOG.append((label, ok))
        log("%-22s hit=%-5s %-30s want_hit=%-5s %s" % (label, got, detail, want_hit, "OK" if ok else "FAIL"))

    # a bay (mid-angle between two column axes) at shaft height must be open all the way across
    gap = 360.0 / N_COL
    bay_x = ORIGIN[0] + 520.0 * math.cos(math.radians(gap / 2.0))
    bay_y = ORIGIN[1] + 520.0 * math.sin(math.radians(gap / 2.0))
    ray("bay is walkable", (bay_x, bay_y, 150.0), (bay_x - 1200.0, bay_y, 150.0), False)
    # the column axis itself must be solid at shaft height (surface at r = 360 + 21.4)
    ray("column axis solid", (ORIGIN[0] + 520.0, ORIGIN[1], 150.0),
        (ORIGIN[0] - 520.0, ORIGIN[1], 150.0), True)
    # cornice crown must be solid above the columns
    ray("cornice solid", (ORIGIN[0], ORIGIN[1], 500.0), (ORIGIN[0], ORIGIN[1], -100.0), True)
    # informational: do the convex hulls also fill the ring's middle? (harmless - that volume
    # is above head height - but it says how coarse the hulls came out)
    ray("centre below arch", (ORIGIN[0], ORIGIN[1], 900.0), (ORIGIN[0], ORIGIN[1], 0.0), True)
    actor_sub.destroy_actor(probe)
    log("probe actor removed")

# ------------------------------------------------- 2. palette rewrite (all nine fields)
# Done BEFORE anything touches the level: in the previous run the palette write reported
# save_packages=False and never reached the disk while a level was open in the same process.
def palette_path_on_disk():
    p = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir())
    return p + "Building/Voxels/Rounded/DA_VoxelBuildPalette.uasset"


pal_disk = palette_path_on_disk()
before = os.stat(pal_disk) if os.path.exists(pal_disk) else None
log("palette on disk before: %s" % ("%d B / %s" % (before.st_size, time.strftime("%H:%M:%S", time.localtime(before.st_mtime)))
                                    if before else "missing"))

pal = wait(PALETTE)
if not pal:
    raise RuntimeError("palette not loadable")
rebuilt = []
for entry in pal.get_editor_property("components") or []:
    copy = unreal.VoxelBuildPrefab()
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
        else:
            log("door repair FAILED for %s" % pid)
            LOG.append(("door_" + pid, False))
    rebuilt = [e for e in rebuilt if str(e.get_editor_property("id")) != pid]
    rebuilt.append(copy)
log("preserved %d existing entries" % len(rebuilt))

stone = wait(STONE, 10.0)
for pid, caption, mesh_path, cells in PIECES:
    mesh = wait(mesh_path, 15.0)
    if not mesh:
        log("SKIP %s: mesh missing" % pid)
        LOG.append((pid, False))
        continue
    actual = dims_of(mesh_path)
    wanted = tuple(c * V for c in cells)
    status = "OK" if actual and all(abs(a - w) < 0.5 for a, w in zip(actual, wanted)) else "MISMATCH"
    log("piece %-20s mesh=%-32s dims=%s wanted=%s %s" % (
        pid, mesh_path.split("/")[-1], actual, wanted, status))
    if status != "OK":
        LOG.append(("dims_" + pid, False))
    entry = unreal.VoxelBuildPrefab()
    entry.set_editor_property("id", pid)
    entry.set_editor_property("display_name", unreal.Text(caption))
    entry.set_editor_property("mesh", mesh)
    entry.set_editor_property("footprint", unreal.IntVector(cells[0], cells[1], cells[2]))
    entry.set_editor_property("surface", stone)
    entry.set_editor_property("pivot_offset_cm", unreal.Vector(0.0, 0.0, 0.0))
    entry.set_editor_property("material", unreal.Name("marble"))
    rebuilt = [e for e in rebuilt if str(e.get_editor_property("id")) != pid]
    rebuilt.append(entry)

pal.modify()
pal.set_editor_property("components", rebuilt)
log("save_packages=%s" % unreal.EditorLoadingAndSavingUtils.save_packages(
    [unreal.load_package(PALETTE)], False))
after = os.stat(pal_disk) if os.path.exists(pal_disk) else None
disk_ok = bool(after and before and (after.st_size != before.st_size or after.st_mtime > before.st_mtime))
LOG.append(("palette_on_disk", disk_ok))
log("palette on disk after: %s -> %s" % (
    "%d B / %s" % (after.st_size, time.strftime("%H:%M:%S", time.localtime(after.st_mtime))) if after else "missing",
    "WROTE" if disk_ok else "UNCHANGED (in-memory only!)"))

# ------------------------------------------------- 4. read back
back = unreal.load_asset(PALETTE)
entries = back.get_editor_property("components") or []
log("palette now holds %d prefabs" % len(entries))
for e in entries:
    mesh = e.get_editor_property("mesh")
    fp = e.get_editor_property("footprint")
    ac = e.get_editor_property("actor_class")
    log("  %-22s %-22s cells %2dx%2dx%-2d actor=%s" % (
        str(e.get_editor_property("id")), str(e.get_editor_property("display_name")),
        fp.x, fp.y, fp.z, ac.get_name() if ac else "-"))
LOG.append(("entries", len(entries) == len(rebuilt)))

verify_collision()

bad = [e for e in LOG if e[1] is False]
log("checks=%d failed=%d -> %s" % (len(LOG), len(bad), [b[0] for b in bad]))
log("RESULT: " + ("PASS" if not bad else "CHECK"))
