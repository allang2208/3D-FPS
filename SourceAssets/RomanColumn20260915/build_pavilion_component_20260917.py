"""Two standalone marble building components: the whole pavilion, and the round-base column.

Piece A  SM_RomanPavilionFull_20 = base + 10 round columns (simplified) + arch + dome merged.
         960 x 960 x 760 cm  ->  footprint 48 x 48 x 38 cells (exact, no margin).
Piece B  SM_RomanColumn_Round_20 (already built), 90 x 90 x 260 cm -> footprint 5 x 5 x 13
         cells: 90 cm is 4.5 cells, so the footprint rounds up and the mesh sits with a 5 cm
         margin per side (the alternative, 4 cells = 80 cm, is smaller than the mesh).

Placement parity (workflow doc 3.8, the "preview is here, the piece lands there" trap): both
pieces are plain prefabs (ActorClass empty), so the ghost preview
(UVoxelBuildComponent::UpdatePrefabPreview, else-branch) and the spawn
(AVoxelBuildWorld::SpawnPrefab) call the identical AVoxelBuildPrefabActor::ComputeTransform,
which centres the mesh's BOUNDS - not its pivot - in the footprint volume. This script
re-implements that formula and prints the resulting world span, so preview and placement can be
compared numerically instead of by eye.

Headless, editor must be closed (the assets are referenced by the level, so the editor's lock
swallows the save):
  UnrealEditor-Cmd <uproject> -run=pythonscript -script=<this> -unattended -NullRHI -nosplash
"""

import math
import os
import time

import unreal

SV = unreal.ModelingService
D = "/Game/Props/RomanColumn20260915"
FULL = D + "/SM_RomanPavilionFull_20"
COLUMN = D + "/SM_RomanColumn_Round_20"
MAT = D + "/M_RomanStone_V2"
PALETTE = "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"
STARTED = time.time()
LOG = []


def log(m):
    print("[full] " + m)


def tf(x=0.0, y=0.0, z=0.0):
    t = unreal.Transform()
    t.translation = unreal.Vector(x, y, z)
    t.rotation = unreal.Rotator(0.0, 0.0, 0.0).quaternion()
    t.scale3d = unreal.Vector(1.0, 1.0, 1.0)
    return t


def handle_of(path):
    r = SV.load_mesh_from_static_mesh(path, 0)
    h = getattr(r, "handle", None)
    if not h or h < 0:
        log("LOAD FAILED %s (%s)" % (path, getattr(r, "message", "")))
    return h


def disk(path):
    full = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()) + \
        path.split("/Game/", 1)[1] + ".uasset"
    if not os.path.exists(full):
        return None
    st = os.stat(full)
    return st.st_size, time.strftime("%H:%M:%S", time.localtime(st.st_mtime)), st.st_mtime


def collision_counts(path):
    mesh = unreal.EditorAssetLibrary.load_asset(path)
    setup = mesh.get_editor_property("body_setup") if mesh else None
    agg = None
    if setup:
        for prop in ("agg_geom", "aggregate_geometry"):
            try:
                agg = setup.get_editor_property(prop)
            except Exception:
                continue
            if agg:
                break
    out = {}
    if agg:
        for elem in ("box_elems", "convex_elems", "sphere_elems", "sphyl_elems", "taper_elems"):
            try:
                arr = agg.get_editor_property(elem)
                out[elem.replace("_elems", "")] = len(arr) if arr else 0
            except Exception:
                pass
    return out


# ------------------------------------------------------------------ piece A
out = SV.create_mesh().handle
base = handle_of(D + "/SM_RomanPavilionBase_20")
arch = handle_of(D + "/SM_RomanPavilionArch_20")
dome = handle_of(D + "/SM_RomanPavilionDome_20")
col = handle_of(COLUMN)

SV.append_mesh_at_transforms(out, base, [tf(0.0, 0.0, 0.0)])
SV.append_mesh_at_transforms(out, arch, [tf(0.0, 0.0, 280.0)])
SV.append_mesh_at_transforms(out, dome, [tf(0.0, 0.0, 360.0)])

# the rack already proved this simplification keeps the silhouette (6.6k of 32.9k tris)
SV.simplify_to_tolerance(col, 0.05, True)
log("column in the piece: %d tris" % SV.get_mesh_info(col).triangle_count)
ring = [tf(360.0 * math.cos(2.0 * math.pi * k / 10), 360.0 * math.sin(2.0 * math.pi * k / 10), 20.0)
        for k in range(10)]
SV.append_mesh_at_transforms(out, col, ring)
for h in (base, arch, dome, col):
    SV.release_mesh(h)

info = SV.get_mesh_info(out)
log("piece A: tris=%d comps=%d open=%d bbox %.0f x %.0f x %.0f  z %.1f..%.1f" % (
    info.triangle_count, info.connected_components, info.open_border_edges,
    info.bounds_max.x - info.bounds_min.x, info.bounds_max.y - info.bounds_min.y,
    info.bounds_max.z - info.bounds_min.z, info.bounds_min.z, info.bounds_max.z))
SV.auto_uv(out, "XAtlas", 0)
SV.save_mesh_to_static_mesh(out, FULL, True, True, False, True)
SV.release_mesh(out)
time.sleep(1.5)
stamp = disk(FULL)
log("piece A on disk: %s" % ("%d B / %s" % (stamp[0], stamp[1]) if stamp else "MISSING"))
LOG.append(("pieceA_on_disk", bool(stamp and stamp[2] >= STARTED - 5)))
if stamp:
    SV.generate_collision(FULL, "AlignedBoxes", 1, 25, True)
    SV.set_asset_materials(FULL, MAT, True)
log("piece A collision: %s" % collision_counts(FULL))


def strip_stray_shapes(path):
    """Drop the sphere/sphyl/taper elements the generators add for round meshes.

    The dome's oversized capsule reached the ground and plugged the whole pavilion before; a
    merged piece inherits it. Boxes stay: one per shell, so the base and the columns keep their
    own boxes and everything above head height is irrelevant to walking.
    """
    mesh = unreal.EditorAssetLibrary.load_asset(path)
    setup = mesh.get_editor_property("body_setup") if mesh else None
    for prop in ("agg_geom", "aggregate_geometry"):
        try:
            agg = setup.get_editor_property(prop)
        except Exception:
            continue
        if not agg:
            continue
        for elem in ("sphere_elems", "sphyl_elems", "taper_elems"):
            try:
                agg.set_editor_property(elem, [])
            except Exception:
                pass
        break
    unreal.EditorLoadingAndSavingUtils.save_packages([unreal.load_package(path)], False)
    return collision_counts(path)


counts = strip_stray_shapes(FULL)
clean = bool(counts.get("box")) and not any(counts.get(k) for k in ("sphere", "sphyl", "taper"))
LOG.append(("pieceA_collision_clean", clean))
log("piece A collision after stripping capsules: %s %s" % (counts, "OK" if clean else "STILL DIRTY"))

# ------------------------------------------------------------------ footprint + parity
log("=== footprint vs mesh, and where ComputeTransform puts each piece ===")
for label, path, cells in (("pavilion_full", FULL, (48, 48, 38)),
                           ("roman_column_round", COLUMN, (5, 5, 13))):
    mesh = unreal.EditorAssetLibrary.load_asset(path)
    bb = mesh.get_bounds()
    size_cm = unreal.Vector(cells[0] * 20.0, cells[1] * 20.0, cells[2] * 20.0)
    exact = (abs(bb.box_extent.x * 2 - size_cm.x) < 0.5 and abs(bb.box_extent.y * 2 - size_cm.y) < 0.5
             and abs(bb.box_extent.z * 2 - size_cm.z) < 0.5)
    log("%-20s mesh %.0f x %.0f x %.0f vs footprint %s = %.0f x %.0f x %.0f -> %s" % (
        label, bb.box_extent.x * 2, bb.box_extent.y * 2, bb.box_extent.z * 2, cells,
        size_cm.x, size_cm.y, size_cm.z,
        "EXACT (bounds == footprint)" if exact else
        "margin %.1f cm per side" % ((size_cm.x - bb.box_extent.x * 2) / 2)))
    for cell in (unreal.IntVector(0, 0, 0), unreal.IntVector(10, -6, 2)):
        # ComputeTransform places the actor so the mesh's BOUNDS land centred in the footprint:
        # actor location = cell*20 + size/2 - bounds.origin, hence mesh centre == cell*20 + size/2
        actor_loc = unreal.Vector(cell.x * 20.0, cell.y * 20.0, cell.z * 20.0) + size_cm * 0.5 - bb.origin
        centre = unreal.Vector(cell.x * 20.0, cell.y * 20.0, cell.z * 20.0) + size_cm * 0.5
        lo = centre - bb.box_extent
        hi = centre + bb.box_extent
        log("   cell %-14s actor at (%.0f,%.0f,%.0f) -> mesh spans x %7.1f..%7.1f  y %7.1f..%7.1f  z %7.1f..%7.1f  (footprint %s..%s)" % (
            (cell.x, cell.y, cell.z), actor_loc.x, actor_loc.y, actor_loc.z,
            lo.x, hi.x, lo.y, hi.y, lo.z, hi.z,
            (cell.x * 20, cell.y * 20, cell.z * 20),
            (cell.x * 20 + size_cm.x, cell.y * 20 + size_cm.y, cell.z * 20 + size_cm.z)))
    LOG.append((label + "_fits", bool(bb.box_extent.x * 2 <= size_cm.x + 0.5 and
                                      bb.box_extent.y * 2 <= size_cm.y + 0.5 and
                                      bb.box_extent.z * 2 <= size_cm.z + 0.5)))

# ------------------------------------------------------------------ palette entries
pal = unreal.EditorAssetLibrary.load_asset(PALETTE)
if not pal:
    log("palette not loadable")
    raise SystemExit(0)
RETIRED = ("pavilion_base", "pavilion_colonnade", "pavilion_dome")
rebuilt = []
for e in pal.get_editor_property("components") or []:
    copy = unreal.VoxelBuildPrefab()
    # all nine fields, copied one by one (a 2026-09-17 regression dropped three of them)
    for field in ("id", "display_name", "mesh", "footprint", "surface", "pivot_offset_cm",
                  "actor_class", "actor_offset_cm", "material"):
        copy.set_editor_property(field, e.get_editor_property(field))
    if str(copy.get_editor_property("id")) not in RETIRED:
        rebuilt.append(copy)
log("kept %d entries, retired %s" % (len(rebuilt), ",".join(RETIRED)))

stone = unreal.EditorAssetLibrary.load_asset(MAT)
for pid, caption, mesh_path, cells in (("pavilion_full", "罗马凉亭（整体）", FULL, (48, 48, 38)),
                                       ("roman_column_round", "圆底罗马柱", COLUMN, (5, 5, 13))):
    mesh = unreal.EditorAssetLibrary.load_asset(mesh_path)
    entry = unreal.VoxelBuildPrefab()
    entry.set_editor_property("id", pid)
    entry.set_editor_property("display_name", unreal.Text(caption))
    entry.set_editor_property("mesh", mesh)
    entry.set_editor_property("footprint", unreal.IntVector(cells[0], cells[1], cells[2]))
    entry.set_editor_property("surface", stone)
    entry.set_editor_property("pivot_offset_cm", unreal.Vector(0.0, 0.0, 0.0))
    entry.set_editor_property("material", unreal.Name("marble"))   # marble row's submenu
    rebuilt = [e for e in rebuilt if str(e.get_editor_property("id")) != pid]
    rebuilt.append(entry)
    log("registered %-20s %-14s cells %s  group=marble (plain prefab: ActorClass empty)" % (pid, caption, cells))

pal.modify()
pal.set_editor_property("components", rebuilt)
log("save_packages=%s" % unreal.EditorLoadingAndSavingUtils.save_packages([unreal.load_package(PALETTE)], False))
stamp = disk(PALETTE)
fresh = bool(stamp and stamp[2] >= STARTED - 5)
LOG.append(("palette_on_disk", fresh))
log("palette on disk: %s %s" % ("%d B / %s" % (stamp[0], stamp[1]) if stamp else "missing",
                                "FRESH" if fresh else "STALE"))

back = unreal.load_asset(PALETTE)
entries = back.get_editor_property("components") or []
log("=== palette read-back (%d entries) ===" % len(entries))
for e in entries:
    fp = e.get_editor_property("footprint")
    m = e.get_editor_property("mesh")
    ac = e.get_editor_property("actor_class")
    bb = m.get_bounds() if m else None
    log("  %-24s %-20s cells %2dx%2dx%-2d mesh %-14s group=%-7s type=%s" % (
        str(e.get_editor_property("id")), str(e.get_editor_property("display_name")),
        fp.x, fp.y, fp.z,
        "%.0fx%.0fx%.0f" % (bb.box_extent.x * 2, bb.box_extent.y * 2, bb.box_extent.z * 2) if bb else "-",
        str(e.get_editor_property("material")),
        "logic" if ac else "plain"))

bad = [x for x in LOG if x[1] is False]
log("checks=%d failed=%d %s" % (len(LOG), len(bad), [b[0] for b in bad]))
log("RESULT: " + ("PASS" if not bad else "CHECK"))
