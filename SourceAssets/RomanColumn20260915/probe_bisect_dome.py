"""Headless bisect: which step of build_pavilion.py's pipeline flattens the dome arc?

Rebuilds the dome exactly like the original script, then stops after each stage and
reports the silhouette (ring count + radius per z), so the collapsing stage is obvious.
"""

import math

import unreal

SV = unreal.ModelingService
V = 20.0
SCRATCH = "/Game/Props/RomanColumn20260915/_ScratchProbeDome"


def tf(x=0.0, y=0.0, z=0.0):
    t = unreal.Transform()
    t.translation = unreal.Vector(x, y, z)
    t.rotation = unreal.Rotator(0.0, 0.0, 0.0).quaternion()
    t.scale3d = unreal.Vector(1.0, 1.0, 1.0)
    return t


def v2(r, z):
    return unreal.Vector2D(r, z)


def profile_summary(handle, label):
    dm = SV.get_dynamic_mesh(handle)
    _, tlist, _ = dm.get_all_triangle_i_ds()
    zs = set()
    for tid in tlist.convert_index_list_to_array():
        ok, v1, v2_, v3 = dm.get_triangle_positions(int(tid))
        for p in (v1, v2_, v3):
            zs.add(round(p.z))
    mid = [z for z in sorted(zs) if 60 < z < 260]
    print("[bisect] %-42s tris=%5d verts=%5d zs_in_60..260=%s" % (
        label, dm.get_triangle_count(), dm.get_vertex_count(), mid[:14] if mid else "NONE (straight cone)"))


def build_dome():
    dome = SV.create_mesh().handle
    SV.append_revolve_polygon(dome, tf(), [v2(14 * V, 0), v2(16 * V, 0), v2(16 * V, 0.8 * V),
                                          v2(15 * V, V), v2(14 * V, V), v2(14 * V, 0)],
                              0.0, 96, 360.0, 0)
    dome_profile = [v2(0, V), v2(14 * V, V)]
    for k in range(1, 19):
        a = math.pi * k / 36.0
        dome_profile.append(v2(14 * V * math.sin(a), V + 14 * V * math.cos(a)))
    dome_profile.append(v2(0, 15 * V))
    SV.append_revolve_polygon(dome, tf(), dome_profile, 0.0, 96, 360.0, 0)
    SV.append_sphere(dome, tf(0, 0, 15 * V), V, 32, 16, "Center", 0)
    return dome


# ---- stage 0: raw revolve + sphere
h = build_dome()
profile_summary(h, "0 raw revolve+sphere")
SV.release_mesh(h)

# ---- stage 1: + self_union(True, True)  (what build_pavilion.py does)
h = build_dome()
try:
    r = SV.self_union(h, True, True)
except TypeError:
    r = SV.self_union(h)
print("[bisect] self_union(True,True) -> %s" % getattr(r, "success", r))
profile_summary(h, "1 + self_union(True,True)")
SV.release_mesh(h)

# ---- stage 2: + self_union(False, False)
h = build_dome()
try:
    r = SV.self_union(h, False, False)
except TypeError:
    r = SV.self_union(h)
print("[bisect] self_union(False,False) -> %s" % getattr(r, "success", r))
profile_summary(h, "2 + self_union(False,False)")
SV.release_mesh(h)

# ---- stage 3: no union, but auto_uv
h = build_dome()
r = SV.auto_uv(h, "XAtlas", 0)
print("[bisect] auto_uv -> %s" % getattr(r, "success", r))
profile_summary(h, "3 raw + auto_uv")
SV.release_mesh(h)

# ---- stage 4: full original publish chain into a scratch asset
h = build_dome()
try:
    SV.self_union(h, True, True)
except TypeError:
    SV.self_union(h)
r = SV.auto_uv(h, "XAtlas", 0)
print("[bisect] auto_uv -> %s" % getattr(r, "success", r))
profile_summary(h, "4 union + auto_uv (pre save)")
r = SV.save_mesh_to_static_mesh(h, SCRATCH, True, True, False, True)
print("[bisect] save(True,True,False,True) -> %s" % getattr(r, "success", r))
a = unreal.EditorAssetLibrary.load_asset(SCRATCH)
if a:
    bb = a.get_bounds()
    print("[bisect] saved asset extent=(%.1f,%.1f,%.1f) tris=%s" % (bb.box_extent.x, bb.box_extent.y,
                                                                    bb.box_extent.z, a.get_num_triangles(0)))
h2 = SV.load_mesh_from_static_mesh(SCRATCH, 0)
profile_summary(SV.get_dynamic_mesh(getattr(h2, "handle", None)), "4b re-read from saved asset")
SV.release_mesh(h)

print("[bisect] RESULT: DONE")
