"""Offline forensics on the three rails: are their faces still facing outward?

The rails were built with self_union(rail, True, True) — the same bTrimFlaps call that flattened
the dome into a cone and broke the baluster's normals. A flipped shell renders as nothing in the
panel icon (single-sided), which is exactly "no preview picture". Dump each rail's triangle soup
and compare the stored face normal against the winding, plus the outward direction from the
piece's centre; also count zero-area faces.
"""

import math
import os
import time

import unreal

SV = unreal.ModelingService
D = "/Game/Props/RomanColumn20260915"
OUT = r"D:\FPS3D\FPSGAME\SourceAssets\RomanColumn20260915\preview_20260917"
PIECES = {"rail100": D + "/SM_RomanRail_100", "rail200": D + "/SM_RomanRail_200",
          "rail300": D + "/SM_RomanRail_300"}


def log(m):
    print("[fx] " + m)


for name, path in PIECES.items():
    r = SV.load_mesh_from_static_mesh(path, 0)
    h = getattr(r, "handle", None)
    if not h or h < 0:
        log("%s LOAD FAILED (%s)" % (name, getattr(r, "message", "")))
        continue
    info = SV.get_mesh_info(h)
    dm = SV.get_dynamic_mesh(h)
    _, tl, _ = dm.get_all_triangle_i_ds()
    arr = tl.convert_index_list_to_array()
    verts = []
    for tid in arr:
        ok, v1, v2, v3 = dm.get_triangle_positions(int(tid))
        fn, _ = dm.get_triangle_face_normal(int(tid))
        verts.append((v1, v2, v3, fn))
    # centre of all vertices (the piece's middle) for the outward test
    n = len(verts)
    cx = sum((v.x for t in verts for v in t[:3])) / (3.0 * n)
    cy = sum((v.y for t in verts for v in t[:3])) / (3.0 * n)
    cz = sum((v.z for t in verts for v in t[:3])) / (3.0 * n)
    flipped = degenerate = outward = 0
    for v1, v2, v3, fn in verts:
        ax, ay, az = (v2.x - v1.x), (v2.y - v1.y), (v2.z - v1.z)
        bx, by, bz = (v3.x - v1.x), (v3.y - v1.y), (v3.z - v1.z)
        # UE winding: clockwise is front-facing, so the geometric normal is b x a
        gx = by * az - bz * ay
        gy = bz * ax - bx * az
        gz = bx * ay - by * ax
        gl = math.sqrt(gx * gx + gy * gy + gz * gz)
        if gl < 1e-9:
            degenerate += 1
            continue
        gx, gy, gz = gx / gl, gy / gl, gz / gl
        if (gx * fn.x + gy * fn.y + gz * fn.z) < 0.5:      # stored normal vs winding
            flipped += 1
        mx = (v1.x + v2.x + v3.x) / 3.0 - cx
        my = (v1.y + v2.y + v3.y) / 3.0 - cy
        mz = (v1.z + v2.z + v3.z) / 3.0 - cz
        ml = math.sqrt(mx * mx + my * my + mz * mz)
        if ml > 1e-6 and (gx * mx + gy * my + gz * mz) / ml > 0.0:
            outward += 1
    log("%-7s tris=%5d comps=%2d closed=%-5s open=%-3d | normal-vs-winding mismatches=%4d (%.1f%%) | "
        "faces pointing away from centre=%d (%.1f%%) | degenerate=%d | bbox %.0fx%.0fx%.0f" % (
            name, info.triangle_count, info.connected_components, info.is_closed,
            info.open_border_edges, flipped, 100.0 * flipped / max(n, 1),
            outward, 100.0 * outward / max(n, 1), degenerate,
            info.bounds_max.x - info.bounds_min.x, info.bounds_max.y - info.bounds_min.y,
            info.bounds_max.z - info.bounds_min.z))
    SV.release_mesh(h)

log("RESULT: DONE")
