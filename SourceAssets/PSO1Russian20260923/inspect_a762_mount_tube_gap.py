"""Quantify ScopeMount vs tube clearance at the clamp contact."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z, TUBE_R = 0.1024, 0.0203

bpy.ops.wm.open_mainfile(filepath=str(O / 'PSO1_A762_Editable.blend'))
body = bpy.data.objects['PSO_ScopeBody']
mount = bpy.data.objects['PSO_ScopeMount']

bv = [body.matrix_world @ v.co for v in body.data.vertices]
bf = [tuple(p.vertices) for p in body.data.polygons]
body_t = BVHTree.FromPolygons(bv, bf)

rows = []
for v in mount.data.vertices:
    w = mount.matrix_world @ v.co
    p = w - DELTA
    r = math.hypot(p.x, p.z - AXIS_Z)
    if not (-0.14 < p.y < 0.05 and r < 0.06 and p.x > 0.0):
        continue
    axis_pt = Vector((0.0, p.y, AXIS_Z)) + DELTA
    direction = (axis_pt - w)
    if direction.length < 1e-8:
        continue
    direction.normalize()
    hit = body_t.ray_cast(w, direction, 0.08)
    gap = None if hit[0] is None else hit[3]
    rows.append({'x': round(p.x, 4), 'y': round(p.y, 4), 'z': round(p.z, 4),
                 'r': round(r, 4), 'gap_mm': None if gap is None else round(gap * 1000, 2)})

rows.sort(key=lambda d: -(d['gap_mm'] or -1))
with_gap = [r for r in rows if r['gap_mm'] is not None]
near = sorted(with_gap, key=lambda d: d['gap_mm'])[:20]
far = with_gap[:20]
bins = {}
for r in with_gap:
    k = round(r['y'] * 20) / 20
    b = bins.setdefault(k, {'n': 0, 'min': 999, 'max': 0, 'rmin': 999})
    b['n'] += 1
    b['min'] = min(b['min'], r['gap_mm']); b['max'] = max(b['max'], r['gap_mm'])
    b['rmin'] = min(b['rmin'], r['r'])

result = {
    'mount_near_tube_verts': len(rows),
    'with_body_hit': len(with_gap),
    'no_body_hit': len(rows) - len(with_gap),
    'nearest_gaps_mm': near,
    'largest_gaps_mm': far,
    'by_y': [{'y': k, **bins[k]} for k in sorted(bins)],
}
(OUT / 'a762_mount_tube_gap.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('A762_MOUNT_TUBE_GAP', json.dumps({'n': len(rows), 'with_hit': len(with_gap),
    'min_gap': near[0] if near else None, 'max_gap': far[0] if far else None,
    'by_y': result['by_y']}), flush=True)
