"""Baluster v3: same classical silhouette, rebuilt WITHOUT self_union (v2 black-patch fix).

Root cause analysis for v2's black patches: self_union rewound/degenerated faces after welding
the overlapping shells; the accepted SM_RomanColumn_Detailed (rebuild_in_editor.py) keeps its
shelves separate with 0.5 cm overlaps and skips union entirely. v3 copies that exact contract.

  plinth box 0-20 | turned revolve 19.5-80.5 | abacus box 80-100, shells NOT merged
  16 shallow flutes on the belly | double astragal at the neck | bevel 0.12 | relief 0.10
  bbox locked 40 x 40 x 100, pivot base centre, footprint 2 x 2 x 5 cells.

Headless:
    UnrealEditor-Cmd FPSGAME.uproject -run=pythonscript -script=<this> -unattended -nosplash
    -nullrhi -nosound -abslog=SourceAssets/RomanColumn20260915/headless_baluster_v3_20260917.log
"""

import math
import time

import unreal

SV = unreal.ModelingService
D = "/Game/Props/RomanColumn20260915"
BALUSTER = D + "/SM_RomanBaluster_Small"
STONE = D + "/M_RomanStone_V2"
DETAIL = D + "/T_Stone_V2_Detail"
PALETTE = "/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette"
V = 20.0
LOG = []


def log(m):
    print("[bal3] " + m)


def tf(x=0.0, y=0.0, z=0.0):
    t = unreal.Transform()
    t.translation = unreal.Vector(x, y, z)
    t.rotation = unreal.Rotator(0.0, 0.0, 0.0).quaternion()
    t.scale3d = unreal.Vector(1.0, 1.0, 1.0)
    return t


def v2(r, z):
    return unreal.Vector2D(r, z)


def do(label, result):
    ok = getattr(result, "success", None)
    LOG.append((label, ok))
    log("%-16s %s" % (label, ok))
    return result


def arc(cr, cz, rad, a0, a1, n):
    return [(cr + rad * math.cos(math.radians(a)), cz + rad * math.sin(math.radians(a)))
            for a in [a0 + (a1 - a0) * i / (n - 1) for i in range(n)]]


def bez(p0, p1, p2, n):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1])
            for t in [i / (n - 1) for i in range(n)]]


def wait(path, timeout=25.0):
    end = time.time() + timeout
    while time.time() < end:
        a = unreal.EditorAssetLibrary.load_asset(path)
        if a:
            return a
        time.sleep(0.3)
    return None


# --------------------------------------------------------------- turned profile
prof = [(0.0, 19.5), (13.0, 19.5)]
prof += arc(15.9, 23.6, 3.35, -75.0, 80.0, 9)                   # lower torus, max r 19.25
prof += [(16.3, 27.0)]                                          # fillet
prof += bez((16.3, 27.0), (12.4, 30.4), (15.7, 33.8), 7)        # scotia
prof += bez((15.7, 33.8), (17.0, 35.4), (15.4, 37.0), 5)        # small upper ring
for i in range(13):                                             # belly with taper
    p = i / 12.0
    prof.append((11.8 + 3.6 * (1 - p) + 3.8 * math.sin(math.pi * min(p * 1.22, 1.0)),
                 37.0 + 28.4 * p))
prof += bez((11.8, 65.4), (13.6, 66.4), (12.1, 67.6), 4)        # astragal 1
prof += [(11.6, 68.2)]                                          # groove between beads
prof += bez((11.6, 68.2), (13.2, 69.1), (11.9, 70.2), 4)        # astragal 2
prof += [(11.2, 70.8)]                                          # neck
prof += bez((11.2, 70.8), (13.4, 76.8), (16.0, 80.3), 8)        # echinus flare
prof += [(0.0, 80.5)]
log("profile points=%d r_max=%.2f" % (len(prof), max(p[0] for p in prof)))

# ------------------------------------------------------- build body (NO union)
bal = SV.create_mesh().handle
SV.append_box(bal, tf(0, 0, 0), 2 * V, 2 * V, V, 0, 0, 0, "Base", 0)          # shell 1
do("revolve", SV.append_revolve_polygon(bal, tf(), prof, 0.0, 64, 360.0, 0))  # shell 2
SV.append_box(bal, tf(0, 0, 4 * V), 1.8 * V, 1.8 * V, V, 0, 0, 0, "Base", 0)  # shell 3
info = SV.get_mesh_info(bal)
log("body: tris=%s comps=%s open=%s closed=%s bbox=(%.1f, %.1f, %.1f) z=%.1f..%.1f" % (
    info.triangle_count, info.connected_components, info.open_border_edges, info.is_closed,
    info.bounds_max.x - info.bounds_min.x, info.bounds_max.y - info.bounds_min.y,
    info.bounds_max.z - info.bounds_min.z, info.bounds_min.z, info.bounds_max.z))

# --------------------------------------------------- 16 shallow flutes, belly only
tool = SV.create_mesh().handle
for i in range(16):
    a = 2 * math.pi * i / 16
    SV.append_cylinder(tool, tf(math.cos(a) * 17.8, math.sin(a) * 17.8, 35.0),
                       1.5, 32.0, 24, 0, True, "Base", 0)
do("flutes", SV.boolean(bal, tool, "Subtract", tf(), True, True))
SV.release_mesh(tool)

# -------------------------------------------------------- bevel + relief + uv
try:
    SV.compute_polygroups(bal, "Angle", 24.0, 2)
    do("bevel", SV.bevel_polygroups(bal, 0.12, 1, 1.0))
except Exception as exc:  # noqa: BLE001
    log("bevel skipped: %s" % exc)
do("uv", SV.auto_uv(bal, "XAtlas", 0))
detail = wait(DETAIL, 10.0)
if detail:
    do("displace", SV.displace_from_texture(bal, "", DETAIL + "." + DETAIL.split("/")[-1], 0.10, 0))
else:
    LOG.append(("displace", False))
    log("displace skipped: detail texture not loadable")

info = SV.get_mesh_info(bal)
size = (info.bounds_max.x - info.bounds_min.x, info.bounds_max.y - info.bounds_min.y,
        info.bounds_max.z - info.bounds_min.z)
log("final: tris=%s comps=%s open=%s closed=%s size=(%.1f, %.1f, %.1f)" % (
    info.triangle_count, info.connected_components, info.open_border_edges,
    info.is_closed, size[0], size[1], size[2]))
geometry_ok = (info.is_closed and info.open_border_edges == 0
               and info.connected_components == 3
               and abs(size[0] - 40) < 0.5 and abs(size[1] - 40) < 0.5
               and abs(size[2] - 100) < 0.5 and abs(info.bounds_min.z) < 0.05)

# --------------------------------------------------------------- save + collide
do("save", SV.save_mesh_to_static_mesh(bal, BALUSTER, True, True, False, True))
SV.release_mesh(bal)
if wait(BALUSTER):
    do("collision", SV.generate_collision(BALUSTER, "ConvexHulls", 8, 25, True))
    do("material", SV.set_asset_materials(BALUSTER, STONE, True))

# ------------------------------------------------------- palette surface re-assert
pal = wait(PALETTE)
if pal:
    rebuilt = []
    for entry in pal.get_editor_property("components") or []:
        copy = unreal.VoxelBuildPrefab()
        copy.set_editor_property("id", entry.get_editor_property("id"))
        copy.set_editor_property("display_name", entry.get_editor_property("display_name"))
        copy.set_editor_property("mesh", entry.get_editor_property("mesh"))
        copy.set_editor_property("footprint", entry.get_editor_property("footprint"))
        copy.set_editor_property("surface", entry.get_editor_property("surface"))
        copy.set_editor_property("pivot_offset_cm", entry.get_editor_property("pivot_offset_cm"))
        if str(copy.get_editor_property("id")) == "baluster_small":
            copy.set_editor_property("surface", wait(STONE, 10.0))
        rebuilt.append(copy)
    pal.modify()
    pal.set_editor_property("components", rebuilt)
    package = unreal.load_package(PALETTE)
    log("palette save_packages=%s" % unreal.EditorLoadingAndSavingUtils.save_packages([package], False))
else:
    LOG.append(("palette", False))
    log("palette not loadable")

# ---------------------------------------------------------------------- readback
asset = unreal.EditorAssetLibrary.load_asset(BALUSTER)
if asset:
    slots = asset.get_editor_property("static_materials")
    slot0 = slots[0].get_editor_property("material_interface") if slots else None
    extent = asset.get_bounds().box_extent
    log("readback slot0=%s dims=(%.1f, %.1f, %.1f)" % (
        slot0.get_path_name().split(".")[-1] if slot0 else "EMPTY",
        extent.x * 2, extent.y * 2, extent.z * 2))

bad = [e for e in LOG if e[1] is False]
log("geometry_ok=%s steps=%d failed=%d" % (geometry_ok, len(LOG), len(bad)))
for label, ok in bad:
    log("  FAILED %s" % label)
log("RESULT: " + ("PASS" if (not bad and geometry_ok) else "CHECK"))
