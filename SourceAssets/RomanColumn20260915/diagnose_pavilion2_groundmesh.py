"""Ground height at the pavilion, read straight from the ground mesh's vertices.

No physics involved: pull the static mesh into a session mesh and look at the triangles near
the pavilion. The move to (1350,-400) was made without re-checking the ground there, and a dip
would leave the stylobate floating high enough that the 40 cm step limit strands the player.
"""

import collections

import unreal

SV = unreal.ModelingService
GROUND = "/Game/GameMaps/Geometry/SM_MainGround_Subdivided"
SITES = {
    "pavilion centre (1350,-400)": (1350.0, -400.0),
    "pavilion edge +X (1830,-400)": (1830.0, -400.0),
    "approach (1350, 100)": (1350.0, 100.0),
    "approach (1350, 300)": (1350.0, 300.0),
    "old pavilion site (1350, 0)": (1350.0, 0.0),
    "colonnade (1350, 600)": (1350.0, 600.0),
    "spawn (0, 0)": (0.0, 0.0),
}
RADIUS = 200.0


def log(m):
    print("[grd] " + m)


loaded = SV.load_mesh_from_static_mesh(GROUND, 0)
handle = getattr(loaded, "handle", None)
if not handle:
    log("cannot load %s" % GROUND)
    raise SystemExit(0)
dm = SV.get_dynamic_mesh(handle)
log("ground mesh: %d tris, %d verts, bounds z %.0f..%.0f" % (
    dm.get_triangle_count(), dm.get_vertex_count(),
    dm.get_mesh_bounds().min.z if hasattr(dm, "get_mesh_bounds") else -999,
    dm.get_mesh_bounds().max.z if hasattr(dm, "get_mesh_bounds") else -999))

_, tlist, _ = dm.get_all_triangle_i_ds()
tarr = tlist.convert_index_list_to_array()
log("triangles: %d" % len(tarr))

samples = {name: [] for name in SITES}
global_z = collections.Counter()
for tid in tarr:
    ok, v1, v2, v3 = dm.get_triangle_positions(int(tid))
    for v in (v1, v2, v3):
        global_z[int(round(v.z / 20.0)) * 20] += 1
        for name, (sx, sy) in SITES.items():
            if abs(v.x - sx) <= RADIUS and abs(v.y - sy) <= RADIUS:
                samples[name].append(v.z)
log("global vertex z histogram (20 cm buckets): %s" % dict(sorted(global_z.items())))
for name in SITES:
    zs = samples[name]
    if not zs:
        log("%-32s no ground vertices within %.0f cm" % (name, RADIUS))
        continue
    log("%-32s z %.1f .. %.1f  (n=%d)" % (name, min(zs), max(zs), len(zs)))
SV.release_mesh(handle)
log("RESULT: DONE")
