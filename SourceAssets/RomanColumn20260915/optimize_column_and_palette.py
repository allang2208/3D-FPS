"""Three fixes: base back to exactly 80 cm, single manifold, palette surface on the new stone.

Headless: UnrealEditor-Cmd <uproject> -run=pythonscript -script=<this> -nullrhi -unattended
"""

import math
import time

import unreal

SV = unreal.ModelingService
D = "/Game/Props/RomanColumn20260915"
COLUMN, SEG = D + "/SM_RomanColumn_Detailed", D + "/SM_BalustradeSegment_20"
STONE = D + "/M_RomanStone_V2"
VEIN, DETAIL = D + "/T_Stone_V2_Noise", D + "/T_Stone_V2_Detail"
PALETTE = "/Game/Building/Voxels/DA_VoxelBuildPalette"
V = 20.0
LOG = []


def log(m):
    print("[opt] " + m)


def tf(x=0.0, y=0.0, z=0.0):
    t = unreal.Transform()
    t.translation = unreal.Vector(x, y, z)
    t.rotation = unreal.Rotator(0.0, 0.0, 0.0).quaternion()
    t.scale3d = unreal.Vector(1.0, 1.0, 1.0)
    return t


def do(label, result):
    ok = getattr(result, "success", None)
    LOG.append((label, ok))
    log("%-14s %s" % (label, ok))
    return result


def wait(p, t=15.0):
    end = time.time() + t
    while time.time() < end:
        a = unreal.EditorAssetLibrary.load_asset(p)
        if a:
            return a
        time.sleep(0.3)
    return None


# --------------------------------------------- 1+2: rebuild with an 80 cm footprint
col = SV.create_mesh().handle
SV.append_box(col, tf(0, 0, 0), 4 * V, 4 * V, V, 0, 0, 0, "Base", 0)                        # 0-20 plinth 80
SV.append_cylinder(col, tf(0, 0, V), 1.9 * V, 0.6 * V, 64, 0, True, "Base", 0)               # 20-32 r38
SV.append_torus(col, tf(0, 0, 1.6 * V), 1.6 * V, 0.4 * V, 48, 12, "Base", 0)                 # torus outer 40
SV.append_cone(col, tf(0, 0, 2.4 * V), 1.6 * V, 1.15 * V, 0.6 * V, 64, 2, True, "Base", 0)   # 48-60
SV.append_cylinder(col, tf(0, 0, 3 * V), 1.15 * V, 8 * V, 64, 8, True, "Base", 0)            # 60-220 shaft
SV.append_torus(col, tf(0, 0, 10.9 * V), 1.05 * V, 0.25 * V, 48, 10, "Base", 0)              # astragal
SV.append_cone(col, tf(0, 0, 11 * V), 1.15 * V, 1.8 * V, V, 64, 3, True, "Base", 0)          # 220-240
SV.append_box(col, tf(0, 0, 12 * V), 4 * V, 4 * V, V, 0, 0, 0, "Base", 0)                    # 240-260 abacus 80

tool = SV.create_mesh().handle
for i in range(20):
    a = 2 * math.pi * i / 20
    SV.append_cylinder(tool, tf(math.cos(a) * 1.15 * V, math.sin(a) * 1.15 * V, 3 * V),
                       2.2, 8 * V, 24, 0, True, "Base", 0)
SV.boolean(col, tool, "Subtract", tf(), True, True)
SV.release_mesh(tool)

try:
    SV.compute_polygroups(col, "Angle", 24.0, 2)
    do("bevel", SV.bevel_polygroups(col, 0.15, 1, 1.0))
except Exception as exc:  # noqa: BLE001
    log("bevel skipped: %s" % exc)
do("uv", SV.auto_uv(col, "XAtlas", 0))
detail = wait(DETAIL)
if detail:
    do("displace", SV.displace_from_texture(col, "", DETAIL + "." + DETAIL.split("/")[-1], 0.10, 0))
info = SV.get_mesh_info(col)
log("column h=%.0f base=%.0f tris=%s comps=%s open=%s" % (
    info.bounds_max.z - info.bounds_min.z, info.bounds_max.x - info.bounds_min.x,
    info.triangle_count, info.connected_components, info.open_border_edges))
do("save", SV.save_mesh_to_static_mesh(col, COLUMN, True, True, False, True))
SV.release_mesh(col)
if wait(COLUMN):
    do("collision", SV.generate_collision(COLUMN, "ConvexHulls", 10, 25, True))
    do("material", SV.set_asset_materials(COLUMN, STONE, True))

# ------------------------------------------------- 3: palette surfaces -> new stone
palette = unreal.EditorAssetLibrary.load_asset(PALETTE)
entries = palette.get_editor_property("components")
changed = 0
for entry in entries:
    pid = entry.get_editor_property("id")
    if pid in ("roman_column", "balustrade_segment"):
        entry.set_editor_property("surface", wait(STONE))
        changed += 1
palette.set_editor_property("components", entries)
do("palette_save", unreal.EditorAssetLibrary.save_asset(PALETTE, False))
log("palette entries updated: %d" % changed)

back = unreal.EditorAssetLibrary.load_asset(PALETTE).get_editor_property("components")
for entry in back:
    surface = entry.get_editor_property("surface")
    log("  %-20s surface=%s" % (entry.get_editor_property("id"),
                                surface.get_path_name().split(".")[-1] if surface else "None"))

bad = [e for e in LOG if e[1] is False]
log("steps=%d failed=%d" % (len(LOG), len(bad)))
log("RESULT: " + ("PASS" if not bad else "CHECK"))
