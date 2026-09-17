"""Headless probe: what profile order does append_revolve_polygon actually need?

Builds several in-memory meshes (nothing saved to disk) and reports the z/radius
histogram so we can see whether a profile produced a curved surface or a chord.
"""

import collections
import math

import unreal

SV = unreal.ModelingService
V = 20.0
R = 280.0


def tf():
    t = unreal.Transform()
    t.translation = unreal.Vector(0.0, 0.0, 0.0)
    t.rotation = unreal.Rotator(0.0, 0.0, 0.0).quaternion()
    t.scale3d = unreal.Vector(1.0, 1.0, 1.0)
    return t


def v2(r, z):
    return unreal.Vector2D(r, z)


def report(label, handle):
    r = SV.load_mesh_from_dynamic_mesh(handle) if False else None
    dm = SV.get_dynamic_mesh(handle)
    print("[probe] --- %s: tris=%d verts=%d closed=%s open=%s comps=%d" % (
        label, dm.get_triangle_count(), dm.get_vertex_count(), dm.get_is_closed_mesh(),
        dm.get_num_open_border_edges(), dm.get_num_connected_components()))
    _, tlist, _ = dm.get_all_triangle_i_ds()
    buckets = collections.defaultdict(list)
    for tid in tlist.convert_index_list_to_array():
        ok, v1, v2_, v3 = dm.get_triangle_positions(int(tid))
        for p in (v1, v2_, v3):
            rr = math.hypot(p.x, p.y)
            buckets[round(p.z)].append(rr)
    for zi in sorted(buckets):
        a = buckets[zi]
        print("[probe]     z=%4d r %.1f..%.1f n=%d" % (zi, min(a), max(a), len(a)))


def arc_points(steps=18, radius=R, base_z=0.0):
    """Hemisphere arc from (radius, base_z) up to (0, base_z+radius), in perimeter order."""
    pts = []
    for k in range(steps + 1):
        a = (math.pi / 2.0) * k / steps
        pts.append(v2(radius * math.cos(a), base_z + radius * math.sin(a)))
    return pts


# --- case A: proper perimeter-ordered closed profile: axis bottom -> rim -> arc -> apex -> axis
prof_a = [v2(0.0, 0.0), v2(R, 0.0)] + arc_points()[1:] + [v2(0.0, 0.0)]
h = SV.create_mesh().handle
SV.append_revolve_polygon(h, tf(), prof_a, 0.0, 48, 360.0, 0)
report("A perimeter-order hemisphere (closed loop back to axis)", h)
SV.release_mesh(h)

# --- case B: open polyline that starts and ends on the axis (no duplicate closing point)
prof_b = [v2(0.0, 0.0), v2(R, 0.0)] + arc_points()[1:]
h = SV.create_mesh().handle
SV.append_revolve_polygon(h, tf(), prof_b, 0.0, 48, 360.0, 0)
report("B polyline axis->rim->arc->apex", h)
SV.release_mesh(h)

# --- case C: the way build_pavilion.py does it (chord + arc + apex, self touching)
prof_c = [v2(0.0, V), v2(14 * V, V)]
for k in range(1, 19):
    a = math.pi * k / 36.0
    prof_c.append(v2(14 * V * math.sin(a), V + 14 * V * math.cos(a)))
prof_c.append(v2(0.0, 15 * V))
h = SV.create_mesh().handle
SV.append_revolve_polygon(h, tf(), prof_c, 0.0, 96, 360.0, 0)
report("C build_pavilion.py profile (the current 'cone')", h)
SV.release_mesh(h)

# --- case D: hemisphere then self_union, to see whether union eats the curvature
prof_d = [v2(0.0, 0.0), v2(R, 0.0)] + arc_points()[1:]
h = SV.create_mesh().handle
SV.append_revolve_polygon(h, tf(), prof_d, 0.0, 48, 360.0, 0)
try:
    SV.self_union(h, True, True)
except TypeError:
    SV.self_union(h)
report("D polyline hemisphere + self_union(True,True)", h)
SV.release_mesh(h)

print("[probe] RESULT: DONE")
