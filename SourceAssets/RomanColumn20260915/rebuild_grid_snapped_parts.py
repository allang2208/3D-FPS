"""Rebuild column and balustrade segment with EVERY band boundary on the 20 cm grid.

Column 260 tall: 20 plinth | 20-60 base | 60-220 shaft | 220-240 capital | 240-260 abacus
Segment 160 tall, 200 long, 40 wide: 20 plinth | 20-40 base | 40-100 shaft | 100-120 abacus | 120-160 rail
Both use the voxel stone material so they match the 20 cm building blocks.
"""

import math
import time

import unreal

SV = unreal.ModelingService
DIR = "/Game/Props/RomanColumn20260915"
COLUMN, SEGMENT = DIR + "/SM_RomanColumn_Detailed", DIR + "/SM_BalustradeSegment_20"
STONE = "/Game/Building/Voxels/M_Voxel_Stone"
V = 20.0
LOG = []


def log(m):
    print("[grid] " + m)


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


def publish(handle, path, hulls):
    do("uv", SV.auto_uv(handle, "XAtlas", 0))
    do("save", SV.save_mesh_to_static_mesh(handle, path, True, True, False, True))
    SV.release_mesh(handle)
    if wait(path):
        do("collision", SV.generate_collision(path, "ConvexHulls", hulls, 25, True))
        do("material", SV.set_asset_materials(path, STONE, True))


# ---------------------------------------------------------- column, bands on grid
col = SV.create_mesh().handle
SV.append_box(col, tf(0, 0, 0), 4 * V, 4 * V, V, 0, 0, 0, "Base", 0)                 # 0-20
SV.append_revolve_polygon(col, tf(), [v2(0, V), v2(2 * V, V), v2(1.75 * V, 2 * V),
                                      v2(1.45 * V, 3 * V), v2(1.2 * V, 3 * V), v2(0, 3 * V)],
                          0.0, 64, 360.0, 0)                                          # 20-60
shaft = [v2(0, 3 * V)]
for k in range(9):                                                                    # 20 cm steps 60..220
    z = 3 * V + k * V
    t = k / 8.0
    shaft.append(v2(1.15 * V - 0.05 * V * t + 0.25 * V * math.sin(math.pi * t), z))
shaft.append(v2(0, 11 * V))
SV.append_revolve_polygon(col, tf(), shaft, 0.0, 64, 360.0, 0)                        # 60-220
SV.append_revolve_polygon(col, tf(), [v2(0, 11 * V), v2(1.2 * V, 11 * V),
                                      v2(1.8 * V, 12 * V), v2(0, 12 * V)], 0.0, 64, 360.0, 0)   # 220-240
SV.append_box(col, tf(0, 0, 12 * V), 4 * V, 4 * V, V, 0, 0, 0, "Base", 0)             # 240-260
tool = SV.create_mesh().handle
for i in range(20):
    a = 2 * math.pi * i / 20
    SV.append_cylinder(tool, tf(math.cos(a) * 1.15 * V, math.sin(a) * 1.15 * V, 3 * V),
                       2.0, 8 * V, 24, 0, True, "Base", 0)                            # flutes 60-220
SV.boolean(col, tool, "Subtract", tf(), True, True)
SV.release_mesh(tool)
try:
    SV.self_union(col, True, True)
except TypeError:
    SV.self_union(col)
i = SV.get_mesh_info(col)
log("column h=%.0f base=%.0f tris=%s comps=%s open=%s" % (
    i.bounds_max.z - i.bounds_min.z, i.bounds_max.x - i.bounds_min.x,
    i.triangle_count, i.connected_components, i.open_border_edges))
publish(col, COLUMN, 10)

# ------------------------------------------------- segment, bands on grid
seg = SV.create_mesh().handle
SV.append_box(seg, tf(0, 0, 0), 10 * V, 2 * V, V, 0, 0, 0, "Base", 0)                # 0-20
SV.append_revolve_polygon(seg, tf(), [v2(0, V), v2(V, V), v2(0.7 * V, 2 * V),
                                      v2(0, 2 * V)], 0.0, 48, 360.0, 0)               # 20-40
bal = [v2(0, 2 * V)]
for k in range(4):                                                                    # 40..100
    z = 2 * V + k * V
    t = k / 3.0
    bal.append(v2(0.7 * V - 0.05 * V * t + 0.12 * V * math.sin(math.pi * t), z))
bal.append(v2(0, 5 * V))
SV.append_revolve_polygon(seg, tf(), bal, 0.0, 48, 360.0, 0)                          # 40-100
SV.append_box(seg, tf(0, 0, 5 * V), 1.8 * V, 1.8 * V, V, 0, 0, 0, "Base", 0)          # 100-120
profile = [v2(-V, 0), v2(V, 0), v2(V, 0.3 * V)]
for k in range(1, 9):
    a = math.pi * k / 18.0
    profile.append(v2(V * math.cos(a), 0.7 * V + 1.3 * V * math.sin(a)))
profile.append(v2(-V, 2 * V))
SV.append_loft(seg, tf(0, 0, 6 * V), profile, [tf(-5 * V, 0, 0), tf(5 * V, 0, 0)], 0) # rail 120-160
SV.append_box(seg, tf(0, 0, 6 * V), 10 * V, 2 * V, 0.4 * V, 0, 0, 0, "Base", 0)
try:
    SV.self_union(seg, True, True)
except TypeError:
    SV.self_union(seg)
s = SV.get_mesh_info(seg)
log("segment size=(%.0f, %.0f, %.0f) tris=%s comps=%s open=%s" % (
    s.bounds_max.x - s.bounds_min.x, s.bounds_max.y - s.bounds_min.y, s.bounds_max.z - s.bounds_min.z,
    s.triangle_count, s.connected_components, s.open_border_edges))
publish(seg, SEGMENT, 6)

# ------------------------------------------------------------------- reseat
sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
moved = 0
for a in sub.get_all_level_actors():
    n = a.get_actor_label()
    loc = a.get_actor_location()
    if n.startswith("Colonnade_C"):
        a.set_actor_location(unreal.Vector(loc.x, loc.y, V), False, False); moved += 1
    elif n.startswith("BalustradeSegment_"):
        a.set_actor_location(unreal.Vector(loc.x, loc.y, V), False, False); moved += 1
    elif n.startswith("Pavilion_Column_"):
        a.set_actor_location(unreal.Vector(loc.x, loc.y, V), False, False); moved += 1
log("resat %d actors on the 20 cm grid" % moved)
try:
    saved = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
except Exception:
    saved = unreal.EditorLevelLibrary.save_current_level()
log("level saved: %s" % saved)
bad = [e for e in LOG if e[1] is False]
log("steps=%d failed=%d" % (len(LOG), len(bad)))
log("RESULT: " + ("PASS" if not bad else "CHECK"))
