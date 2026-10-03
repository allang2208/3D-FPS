"""Measure cylinder-wall gaps on A762 PSO_ScopeBody; report hole extent for patch."""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z, R = 0.1024, 0.0200

bpy.ops.wm.open_mainfile(filepath=str(OUT / 'PSO1_A762_Editable.before-tuck.blend'))
body = bpy.data.objects['PSO_ScopeBody']
mw = body.matrix_world
verts = [(mw @ v.co) - DELTA for v in body.data.vertices]
faces = [tuple(p.vertices) for p in body.data.polygons]
tree = BVHTree.FromPolygons(verts, faces)

# Sample cylinder wall: radial rays from outside inward
ys = [i * 0.005 - 0.12 for i in range(50)]  # -0.12 .. 0.125
angs = [math.radians(a) for a in range(-120, 121, 5)]  # mount-side heavy
gaps = []
for y in ys:
    for a in angs:
        # point on cylinder, ray from 1.6R toward axis
        ox = math.cos(a); oz = math.sin(a)
        start = Vector((1.6*R*ox, y, AXIS_Z + 1.6*R*oz))
        direction = Vector((-ox, 0, -oz))  # toward axis in xz
        h = tree.ray_cast(start, direction, 1.2*R)
        if h[0] is None:
            gaps.append({'y': round(y,4), 'ang': round(math.degrees(a),1),
                         'kind': 'miss'})
            continue
        hit = h[0]
        hr = math.hypot(hit.x, hit.z - AXIS_Z)
        # if first hit is well inside tube wall band, outer shell missing
        if hr < 0.0175:
            gaps.append({'y': round(y,4), 'ang': round(math.degrees(a),1),
                         'kind': 'deep', 'hr': round(hr,4)})

# Cluster gaps
from collections import defaultdict
bins = defaultdict(list)
for g in gaps:
    key = (round(g['y']/0.02)*0.02, round(g['ang']/15)*15)
    bins[key].append(g)

clusters = []
for (y, ang), items in sorted(bins.items(), key=lambda kv: -len(kv[1])):
    if len(items) < 3:
        continue
    clusters.append({'y': y, 'ang': ang, 'n': len(items),
                     'kinds': {k: sum(1 for i in items if i['kind']==k)
                               for k in ('miss','deep')}})

# Also: find largest open boundary loops that are NOT bore (center far from axis)
bm = bmesh.new(); bm.from_mesh(body.data)
bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table()
for v in bm.verts:
    v.co = (mw @ v.co) - DELTA

def loops_from_boundary():
    used = set(); out = []
    bedges = [e for e in bm.edges if e.is_boundary]
    for e0 in bedges:
        if e0.index in used:
            continue
        loop = []; e = e0; v = e.verts[0]
        guard = 0
        while e.index not in used and guard < 10000:
            used.add(e.index); loop.append(e); v = e.other_vert(v); guard += 1
            nxt = None
            for e2 in v.link_edges:
                if e2.is_boundary and e2.index not in used:
                    nxt = e2; break
            if nxt is None:
                break
            e = nxt
        if len(loop) >= 6:
            pts = []
            for e in loop:
                pts.extend([e.verts[0].co, e.verts[1].co])
            # unique-ish
            cx = sum(p.x for p in pts)/len(pts)
            cy = sum(p.y for p in pts)/len(pts)
            cz = sum(p.z for p in pts)/len(pts)
            rs = [math.hypot(p.x, p.z-AXIS_Z) for p in pts]
            ys = [p.y for p in pts]
            angs = [math.degrees(math.atan2(p.z-AXIS_Z, p.x)) for p in pts]
            cr = math.hypot(cx, cz-AXIS_Z)
            bore = cr < 0.012 and max(rs) < 0.026
            out.append({
                'n': len(loop), 'c': [round(cx,4), round(cy,4), round(cz,4)],
                'cr': round(cr,4), 'r': [round(min(rs),4), round(max(rs),4)],
                'y': [round(min(ys),4), round(max(ys),4)],
                'ang': [round(min(angs),1), round(max(angs),1)],
                'bore': bore,
            })
    return out

all_loops = loops_from_boundary()
nonbore = [L for L in all_loops if not L['bore']]
nonbore.sort(key=lambda L: -L['n'])

# Focus ROI around silhouette hole
roi = [L for L in nonbore
       if L['y'][0] < 0.05 and L['y'][1] > -0.10
       and L['c'][0] > -0.02]

report = {
    'gap_samples': len(gaps),
    'gap_clusters_top': clusters[:25],
    'boundary_total': sum(1 for e in bm.edges if e.is_boundary),
    'nonbore_loops_top15': nonbore[:15],
    'roi_nonbore': roi[:20],
}
bm.free()
(OUT / 'a762_cyl_gaps.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('A762_CYL_GAPS', json.dumps({
    'gaps': len(gaps), 'clusters': len(clusters),
    'top3': clusters[:3], 'roi_loops': len(roi),
    'top_roi': roi[:5],
}), flush=True)
