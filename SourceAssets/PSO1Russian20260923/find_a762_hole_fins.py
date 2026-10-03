"""Locate the rectangular body hole + fins near the rivet plate; report SVD body bounds."""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets')
OUT = O / 'PSO1Russian20260923/inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z = 0.1024

bpy.ops.wm.open_mainfile(filepath=str(O/'PSO1Russian20260923/PSO1_A762_Editable.blend'))
body = bpy.data.objects['PSO_ScopeBody']
mw = body.matrix_world
bm = bmesh.new(); bm.from_mesh(body.data); bm.faces.ensure_lookup_table(); bm.edges.ensure_lookup_table()

def src(co):
    return (mw @ co) - DELTA

# High-aspect / tiny faces near mid body (fins)
fins = []
for f in bm.faces:
    pts = [src(v.co) for v in f.verts]
    cy = sum(p.y for p in pts)/len(pts)
    if not (-0.08 <= cy <= 0.08):
        continue
    # edge lengths
    lens = []
    for i in range(len(pts)):
        lens.append((pts[i] - pts[(i+1)%len(pts)]).length)
    if min(lens) < 1e-9:
        continue
    aspect = max(lens) / min(lens)
    area = f.calc_area()
    c = sum(pts, Vector())/len(pts)
    r = math.hypot(c.x, c.z - AXIS_Z)
    if aspect > 12 or area < 1.5e-6:
        fins.append({'fi': f.index, 'aspect': round(aspect,1), 'area': round(area,8),
                     'c': [round(c.x,4), round(c.y,4), round(c.z,4)], 'r': round(r,4)})

fins.sort(key=lambda d: -d['aspect'])

# Boundary edges near the hole: y in [-0.05, 0.06], r in [0.018, 0.045], not deep foot
hole_edges = []
for e in bm.edges:
    if not e.is_boundary: continue
    mid = src((e.verts[0].co + e.verts[1].co)*0.5)
    r = math.hypot(mid.x, mid.z - AXIS_Z)
    if -0.05 <= mid.y <= 0.06 and 0.018 <= r <= 0.05 and mid.z > 0.07:
        hole_edges.append({'x': round(mid.x,4), 'y': round(mid.y,4), 'z': round(mid.z,4), 'r': round(r,4), 'ei': e.index})

# Walk loops from these edges
used=set(); loops=[]
emap={e.index:e for e in bm.edges}
cset=set(h['ei'] for h in hole_edges)
for ei0 in list(cset):
    if ei0 in used: continue
    e0=emap[ei0]; loop=[]; e=e0; v=e.verts[0]
    while e.index not in used:
        used.add(e.index); loop.append(e); v=e.other_vert(v)
        nxt=None
        for e2 in v.link_edges:
            if e2.is_boundary and e2.index in cset and e2.index not in used:
                nxt=e2; break
        if not nxt: break
        e=nxt
    if len(loop) >= 6:
        pts=[src(vv.co) for ed in loop for vv in ed.verts]
        cx=sum(p.x for p in pts)/len(pts); cy=sum(p.y for p in pts)/len(pts); cz=sum(p.z for p in pts)/len(pts)
        loops.append({'n': len(loop), 'c': [round(cx,4), round(cy,4), round(cz,4)],
                      'r': round(math.hypot(cx, cz-AXIS_Z),4),
                      'y': [round(min(p.y for p in pts),4), round(max(p.y for p in pts),4)],
                      'z': [round(min(p.z for p in pts),4), round(max(p.z for p in pts),4)],
                      'x': [round(min(p.x for p in pts),4), round(max(p.x for p in pts),4)]})
loops.sort(key=lambda L: -L['n'])
bm.free()

# SVD bounds
bpy.ops.wm.open_mainfile(filepath=str(O/'SVDMatteDetail20260923/SVD_MatteDetail_Editable.blend'))
ob=bpy.data.objects['SM_SVD_ScopeBody']
xs,ys,zs=[],[],[]
for v in ob.data.vertices:
    p=ob.matrix_world@v.co; xs.append(p.x); ys.append(p.y); zs.append(p.z)
svd_bounds={'x':[min(xs),max(xs)],'y':[min(ys),max(ys)],'z':[min(zs),max(zs)],
            'center':[(min(xs)+max(xs))/2,(min(ys)+max(ys))/2,(min(zs)+max(zs))/2]}

result={'fins_top20': fins[:20], 'fin_count': len(fins), 'hole_loops': loops[:12], 'svd_bounds': svd_bounds}
(OUT/'a762_hole_fins.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('HOLE_FINS', json.dumps({'fin_count': len(fins), 'fins_top8': fins[:8], 'hole_loops': loops[:8], 'svd_center': svd_bounds['center']}), flush=True)
