"""Classify uncovered body/mount openings excluding the optical bore."""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z = 0.1024

bpy.ops.wm.open_mainfile(filepath=str(O / 'PSO1_A762_Editable.blend'))
body = bpy.data.objects['PSO_ScopeBody']
mount = bpy.data.objects['PSO_ScopeMount']
lens = bpy.data.objects['PSO_ScopeLens']


def build(ob, skip_glass=False):
    mw = ob.matrix_world
    verts = [mw @ v.co for v in ob.data.vertices]
    faces = []
    for p in ob.data.polygons:
        mat = ob.data.materials[p.material_index] if ob.data.materials else None
        if skip_glass and mat and 'OpticalGlass' in mat.name:
            continue
        faces.append(tuple(p.vertices))
    return verts, faces, BVHTree.FromPolygons(verts, faces)

bv, bf, body_t = build(body)
mv, mf, mount_t = build(mount)
lv, lf, lens_t = build(lens, skip_glass=True)
all_v = bv + mv + lv
all_f = bf + [tuple(len(bv)+i for i in f) for f in mf] + [tuple(len(bv)+len(mv)+i for i in f) for f in lf]
opaque = BVHTree.FromPolygons(all_v, all_f)


def uncovered_edges(ob, other_trees):
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.edges.ensure_lookup_table()
    mw = ob.matrix_world
    rows = []
    for e in bm.edges:
        if not e.is_boundary:
            continue
        mid_w = mw @ ((e.verts[0].co + e.verts[1].co) * 0.5)
        f = e.link_faces[0]
        n = (mw.to_3x3() @ f.normal).normalized()
        covered = False
        for tree in other_trees:
            h = tree.ray_cast(mid_w + n * 0.0004, n, 0.005)
            if h[0] is not None:
                covered = True; break
            h = tree.ray_cast(mid_w - n * 0.0002, n, 0.008)
            if h[0] is not None:
                covered = True; break
        p = mid_w - DELTA
        r = math.hypot(p.x, p.z - AXIS_Z)
        bore = r < 0.023
        if not covered and not bore:
            rows.append({'x': round(p.x, 4), 'y': round(p.y, 4), 'z': round(p.z, 4), 'r': round(r, 4)})
    bm.free()
    return rows

body_open = uncovered_edges(body, [opaque])
mount_open = uncovered_edges(mount, [opaque])

def cluster(rows):
    bins = {}
    for r in rows:
        key = (round(r['x'] * 25) / 25, round(r['y'] * 25) / 25, round(r['z'] * 25) / 25)
        bins[key] = bins.get(key, 0) + 1
    return sorted(({'xyz': list(k), 'n': n} for k, n in bins.items()), key=lambda d: -d['n'])

# Cross gap: from body verts near mount, distance to mount
gaps = []
mw = body.matrix_world
for v in body.data.vertices:
    p = mw @ v.co
    src = p - DELTA
    if not (0.015 < src.x < 0.045 and -0.12 < src.y < 0.05 and 0.02 < src.z < 0.09):
        continue
    loc, normal, index, dist = mount_t.find_nearest(p)
    if loc is not None and dist > 0.001:
        gaps.append({'x': round(src.x, 4), 'y': round(src.y, 4), 'z': round(src.z, 4), 'gap_mm': round(dist * 1000, 2)})
gaps.sort(key=lambda d: -d['gap_mm'])

result = {
    'body_exposed_nonbore_edges': len(body_open),
    'body_clusters': cluster(body_open)[:20],
    'mount_exposed_nonbore_edges': len(mount_open),
    'mount_clusters': cluster(mount_open)[:20],
    'body_to_mount_gap_gt_1mm': len(gaps),
    'largest_gaps': gaps[:25],
}
(OUT / 'a762_body_open_classified.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('A762_BODY_OPEN_CLASSIFIED', json.dumps(result), flush=True)
