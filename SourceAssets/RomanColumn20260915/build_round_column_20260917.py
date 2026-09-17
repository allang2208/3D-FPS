"""Pavilion-only column: round base plinth and round abacus (v4).

Pick each square plate by a corner point (select_connected), delete that shell, then read the
plate's own height off the mesh bounds that remain — no selection-bounds API (it returns
nothing in this binding) and no z-band heuristics (they cut the capital).
"""

import os
import time

import unreal

SV = unreal.ModelingService
DIR = "/Game/Props/RomanColumn20260915"
SRC = DIR + "/SM_RomanColumn_Detailed"
DST = DIR + "/SM_RomanColumn_Round_20"
MAT = DIR + "/M_RomanStone_V2"
STARTED = time.time()


def log(m):
    print("[r4] " + m)


def tf(x=0.0, y=0.0, z=0.0):
    t = unreal.Transform()
    t.translation = unreal.Vector(x, y, z)
    t.rotation = unreal.Rotator(0.0, 0.0, 0.0).quaternion()
    t.scale3d = unreal.Vector(1.0, 1.0, 1.0)
    return t


def disk(path):
    full = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()) + \
        path.split("/Game/", 1)[1] + ".uasset"
    if not os.path.exists(full):
        return None
    st = os.stat(full)
    return st.st_size, time.strftime("%H:%M:%S", time.localtime(st.st_mtime)), st.st_mtime


loaded = SV.load_mesh_from_static_mesh(SRC, 0)
handle = getattr(loaded, "handle", None)
if not handle or handle < 0:
    log("LOAD FAILED")
    raise SystemExit(0)
src = SV.get_mesh_info(handle)
log("source: tris=%d comps=%d bbox %.0f x %.0f x %.0f" % (
    src.triangle_count, src.connected_components,
    src.bounds_max.x - src.bounds_min.x, src.bounds_max.y - src.bounds_min.y,
    src.bounds_max.z - src.bounds_min.z))
work = getattr(SV.copy_mesh(handle), "handle", None)
SV.release_mesh(handle)

# --- base plinth: a point at the plate's corner is inside that shell only
SV.select_connected(work, "plinth", unreal.Vector(38.5, 38.5, 8.0))
n = SV.selection_count(work, "plinth")
SV.delete_faces(work, "plinth")
info = SV.get_mesh_info(work)
plinth_top = info.bounds_min.z
log("base plinth: removed %d tris, remaining min z = %.2f -> plinth height %.2f, disc r45" % (n, plinth_top, plinth_top))
SV.append_cylinder(work, tf(0.0, 0.0, 0.0), 45.0, plinth_top, 48, 0, True, "Base", 0)

# --- abacus: same trick at the top corner
SV.select_connected(work, "abacus", unreal.Vector(38.5, 38.5, 250.0))
n2 = SV.selection_count(work, "abacus")
SV.delete_faces(work, "abacus")
info = SV.get_mesh_info(work)
capital_top = info.bounds_max.z
log("abacus: removed %d tris, remaining max z = %.2f -> abacus %.2f..260" % (
    n2, capital_top, capital_top))
SV.append_cylinder(work, tf(0.0, 0.0, capital_top), 40.0, 260.0 - capital_top, 48, 0, True, "Base", 0)

info = SV.get_mesh_info(work)
ok = (abs((info.bounds_max.x - info.bounds_min.x) - 90.0) < 1.0 and
      abs((info.bounds_max.y - info.bounds_min.y) - 90.0) < 1.0 and
      abs((info.bounds_max.z - info.bounds_min.z) - 260.0) < 1.0 and
      info.open_border_edges == 0 and
      n > 10 and n2 > 10 and
      abs(info.triangle_count - (src.triangle_count + 96 * 4)) < 400)
log("final: tris=%d comps=%d open=%d bbox %.0f x %.0f x %.0f  z %.1f..%.1f  -> %s" % (
    info.triangle_count, info.connected_components, info.open_border_edges,
    info.bounds_max.x - info.bounds_min.x, info.bounds_max.y - info.bounds_min.y,
    info.bounds_max.z - info.bounds_min.z, info.bounds_min.z, info.bounds_max.z,
    "OK" if ok else "FAILED"))
if ok:
    SV.auto_uv(work, "XAtlas", 0)
    SV.save_mesh_to_static_mesh(work, DST, True, True, False, True)
SV.release_mesh(work)
time.sleep(1.5)
stamp = disk(DST)
log("disk: %s" % ("%d B / %s" % (stamp[0], stamp[1]) if stamp else "MISSING"))
if stamp and ok:
    SV.generate_collision(DST, "AlignedBoxes", 1, 25, True)
    SV.set_asset_materials(DST, MAT, True)
    asset = unreal.EditorAssetLibrary.load_asset(DST)
    bb = asset.get_bounds()
    log("asset: bbox %.0f x %.0f x %.0f origin z=%.1f tris=%d" % (
        bb.box_extent.x * 2, bb.box_extent.y * 2, bb.box_extent.z * 2, bb.origin.z,
        asset.get_num_triangles(0)))
log("RESULT: %s" % ("PASS" if stamp and ok and stamp[2] >= STARTED - 5 else "CHECK"))
