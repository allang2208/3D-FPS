"""Locate real near-wall gaps on cylinder (opposite-wall hits count as holes)."""
import bpy, json, math
from pathlib import Path
from collections import defaultdict
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

ys = [round(i * 0.004 - 0.100, 4) for i in range(55)]
angs = [math.radians(a) for a in range(-150, 151, 4)]
gaps = []
solid = 0
for y in ys:
    for a in angs:
        ox, oz = math.cos(a), math.sin(a)
        start = Vector((1.7*R*ox, y, AXIS_Z + 1.7*R*oz))
        direction = Vector((-ox, 0.0, -oz))
        h = tree.ray_cast(start, direction, 2.4*R)
        if h[0] is None:
            gaps.append((y, a, 'miss')); continue
        hit = h[0]
        hx, hz = hit.x, hit.z - AXIS_Z
        hr = math.hypot(hx, hz)
        # near-side if hit is still on same angular half-plane
        same_side = (hx*ox + hz*oz) > 0
        if (not same_side) or hr < 0.0170 or hr > 0.0280:
            kind = 'opp' if not same_side else ('deep' if hr < 0.0170 else 'far')
            gaps.append((y, round(math.degrees(a),1), kind, round(hr,4), round(y,4)))
        else:
            solid += 1

# rebuild with proper dicts
gaps_d = []
for y in ys:
    for a in angs:
        ox, oz = math.cos(a), math.sin(a)
        start = Vector((1.7*R*ox, y, AXIS_Z + 1.7*R*oz))
        direction = Vector((-ox, 0.0, -oz))
        h = tree.ray_cast(start, direction, 2.4*R)
        if h[0] is None:
            gaps_d.append({'y': y, 'ang': round(math.degrees(a),1), 'kind': 'miss', 'hr': None})
            continue
        hit = h[0]
        hx, hz = hit.x, hit.z - AXIS_Z
        hr = math.hypot(hx, hz)
        same_side = (hx*ox + hz*oz) > 0.0
        if (not same_side) or hr < 0.0170 or hr > 0.0285:
            kind = 'opp' if not same_side else ('deep' if hr < 0.0170 else 'outr')
            gaps_d.append({'y': y, 'ang': round(math.degrees(a),1), 'kind': kind, 'hr': round(hr,4)})

bins = defaultdict(list)
for g in gaps_d:
    key = (round(g['y']/0.012)*0.012, round(g['ang']/12)*12)
    bins[key].append(g)
clusters = []
for (y, ang), items in sorted(bins.items(), key=lambda kv: -len(kv[1])):
    if len(items) < 4:
        continue
    kinds = {}
    for i in items:
        kinds[i['kind']] = kinds.get(i['kind'], 0) + 1
    clusters.append({'y': round(y,3), 'ang': ang, 'n': len(items), 'kinds': kinds})

# Bounding box of largest contiguous gap region near mount (ang -90..+40, y -0.09..0.05)
roi = [g for g in gaps_d if -0.09 <= g['y'] <= 0.05 and -100 <= g['ang'] <= 50]
ys_r = [g['y'] for g in roi]; angs_r = [g['ang'] for g in roi]
extent = None
if roi:
    extent = {'y': [min(ys_r), max(ys_r)], 'ang': [min(angs_r), max(angs_r)], 'n': len(roi)}

# Find connected components in (y,ang) grid for ROI gaps
gap_set = {(g['y'], g['ang']) for g in roi}
# flood fill
visited = set(); components = []
for seed in list(gap_set):
    if seed in visited:
        continue
    stack = [seed]; comp = []
    while stack:
        p = stack.pop()
        if p in visited or p not in gap_set:
            continue
        visited.add(p); comp.append(p)
        y, ang = p
        for dy in (-0.004, 0, 0.004):
            for da in (-4, 0, 4):
                stack.append((round(y+dy,4), round(ang+da,1)))
    if len(comp) >= 8:
        cy = sum(p[0] for p in comp)/len(comp)
        ca = sum(p[1] for p in comp)/len(comp)
        components.append({
            'n': len(comp),
            'y': [min(p[0] for p in comp), max(p[0] for p in comp)],
            'ang': [min(p[1] for p in comp), max(p[1] for p in comp)],
            'cy': round(cy,4), 'cang': round(ca,1),
        })
components.sort(key=lambda c: -c['n'])

report = {
    'solid': solid,
    'gaps': len(gaps_d),
    'roi_extent': extent,
    'components': components[:10],
    'clusters_top20': clusters[:20],
}
(OUT / 'a762_nearwall_gaps.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('NEARWALL', json.dumps({
    'gaps': len(gaps_d), 'solid': solid,
    'extent': extent, 'components': components[:5],
}), flush=True)
