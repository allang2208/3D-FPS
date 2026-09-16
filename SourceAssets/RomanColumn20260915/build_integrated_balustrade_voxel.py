"""Integrated, voxel-aligned balustrade segment + single-manifold column.

Segment is ONE mesh: 200 x 40 x 160 (10 x 2 x 8 voxels of 20 cm)
  0-20    base plinth 200 x 40 x 20
  20-120  turned baluster (40 x 40 foot, 60 shaft, 40 abacus)
  120-160 moulded top rail 200 x 40 x 40 (swept cross-section, same width as the plinth)
Rail and plinth share the same 40 cm width so the piece is symmetric and the rail covers the base.
"""

import math
import time

import unreal

SV = unreal.ModelingService
DIR = "/Game/Props/RomanColumn20260915"
SEGMENT = DIR + "/SM_BalustradeSegment_20"
COLUMN = DIR + "/SM_RomanColumn_Detailed"
PLASTER = DIR + "/M_Plaster_Detailed"
V = 20.0
LOG = []


def log(m):
    print("[seg] " + m)


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
    LOG.append((label, ok))
    log("%-18s %s" % (label, ok))
    return result


def wait(path, timeout=15.0):
    end = time.time() + timeout
    while time.time() < end:
        a = unreal.EditorAssetLibrary.load_asset(path)
        if a:
            return a
        time.sleep(0.3)
    return None


def save_and_collide(handle, path, method, hulls):
    do("uv", SV.auto_uv(handle, "XAtlas", 0))
    do("save", SV.save_mesh_to_static_mesh(handle, path, True, True, False, True))
    SV.release_mesh(handle)
    if wait(path):
        do("collision", SV.generate_collision(path, method, hulls, 25, True))
        do("material", SV.set_asset_materials(path, PLASTER, True))


# ------------------------------------------------------------ column: 1 shell
col = SV.create_mesh().handle
SV.append_box(col, tf(0, 0, 0), 4 * V, 4 * V, V, 0, 0, 0, "Base", 0)
SV.append_revolve_polygon(col, tf(), [v2(0, 0.5 * V), v2(2 * V, 0.5 * V), v2(2 * V, 2.2 * V),
                                      v2(1.8 * V, 2.5 * V), v2(1.5 * V, 2.9 * V), v2(1.4 * V, 3.2 * V),
                                      v2(0, 3.2 * V)], 0.0, 64, 360.0, 0)
shaft = [v2(0, 3 * V)]
for k in range(25):
    z = 3 * V + 8 * V * k / 24.0
    t = (z - 3 * V) / (8 * V)
    r = 1.1 * V - 0.8 + 0.55 * math.sin(math.pi * min(t / 0.62, 1.0))
    shaft.append(v2(r + (0.6 * V if k == 0 else 0.35 * V), z))
shaft.append(v2(0, 11.2 * V))
SV.append_revolve_polygon(col, tf(), shaft, 0.0, 64, 360.0, 0)
SV.append_revolve_polygon(col, tf(), [v2(0, 10.8 * V), v2(1.2 * V, 10.8 * V), v2(1.5 * V, 11.6 * V),
                                      v2(1.8 * V, 12.2 * V), v2(0, 12.2 * V)], 0.0, 64, 360.0, 0)
SV.append_box(col, tf(0, 0, 11.5 * V), 4 * V, 4 * V, V, 0, 0, 0, "Base", 0)
tool = SV.create_mesh().handle
for i in range(20):
    a = 2 * math.pi * i / 20
    SV.append_cylinder(tool, tf(math.cos(a) * 1.1 * V, math.sin(a) * 1.1 * V, 2.1 * V), 2.0, 15 * V, 24, 0, True, "Base", 0)
SV.boolean(col, tool, "Subtract", tf(), True, True)
SV.release_mesh(tool)
try:
    SV.self_union(col, True, True)
except TypeError:
    SV.self_union(col)
i = SV.get_mesh_info(col)
log("column tris=%s comps=%s open=%s h=%.0f" % (i.triangle_count, i.connected_components, i.open_border_edges,
                                                i.bounds_max.z - i.bounds_min.z))
save_and_collide(col, COLUMN, "ConvexHulls", 10)

# ------------------------------------------------ integrated balustrade segment
seg = SV.create_mesh().handle
SV.append_box(seg, tf(0, 0, 0), 10 * V, 2 * V, V, 0, 0, 0, "Base", 0)                      # 0-20
SV.append_revolve_polygon(seg, tf(), [v2(0, V), v2(V, V), v2(V, 1.5 * V), v2(0.8 * V, 1.9 * V),
                                      v2(0.8 * V, 2.2 * V), v2(0.65 * V, 3.5 * V), v2(0.7 * V, 5 * V),
                                      v2(0.6 * V, 5.6 * V), v2(0, 5.6 * V)], 0.0, 48, 360.0, 0)
SV.append_box(seg, tf(0, 0, 5.5 * V), 1.8 * V, 1.8 * V, 0.5 * V, 0, 0, 0, "Base", 0)        # 110-120
rail_profile = [v2(-V, 0), v2(V, 0), v2(V, 0.3 * V)]
for k in range(1, 9):
    a = math.pi * k / 18.0
    rail_profile.append(v2(V * math.cos(a), 0.7 * V + 1.3 * V * math.sin(a)))
rail_profile.append(v2(-V, 2 * V))
SV.append_loft(seg, tf(0, 0, 6 * V), rail_profile, [tf(-5 * V, 0, 0), tf(5 * V, 0, 0)], 0)
SV.append_box(seg, tf(0, 0, 6 * V), 10 * V, 2 * V, 0.4 * V, 0, 0, 0, "Base", 0)            # rail foot band
try:
    SV.self_union(seg, True, True)
except TypeError:
    SV.self_union(seg)
s = SV.get_mesh_info(seg)
log("segment tris=%s comps=%s open=%s size=(%.0f, %.0f, %.0f)" % (
    s.triangle_count, s.connected_components, s.open_border_edges,
    s.bounds_max.x - s.bounds_min.x, s.bounds_max.y - s.bounds_min.y, s.bounds_max.z - s.bounds_min.z))
save_and_collide(seg, SEGMENT, "AlignedBoxes", 1)

# ------------------------------------------------------------------- replace
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for a in list(sub.get_all_level_actors()):
    n = a.get_actor_label()
    if n.startswith("Baluster_") or n in ("Balustrade_Plinth", "BalustradeRail_Top", "BalustradeRail_Bottom"):
        sub.destroy_actor(a)
log("old fence actors removed")

placed = 0
for k in range(8):
    if getattr(SV.spawn_static_mesh_actor(SEGMENT, tf(600.0 + 200.0 * k, 930.0, 20.0),
                                          "BalustradeSegment_%02d" % (k + 1)), "success", False):
        placed += 1
log("segments placed: %d" % placed)
try:
    saved = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception:
    saved = unreal.EditorLevelLibrary.save_current_level()
log("level saved: %s" % saved)
bad = [e for e in LOG if e[1] is False]
log("steps=%d failed=%d" % (len(LOG), len(bad)))
log("RESULT: " + ("PASS" if not bad else "CHECK"))
