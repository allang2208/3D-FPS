"""Find the largest non-bore body boundary loops and characterize the hollow."""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z = 0.1024

bpy.ops.wm.open_mainfile(filepath=str(O / 'PSO1_A762_Editable.blend'))
body = bpy.data.objects['PSO_ScopeBody']
mw = body.matrix_world
bm = bmesh.new(); bm.from_mesh(body.data); bm.edges.ensure_lookup_table(); bm.verts.ensure_lookup_table()

def src(co):
    return (mw @ co) - DELTA

boundary = [e for e in bm.edges if e.is_boundary]
used = set()
loops = []
for e0 in boundary:
    if e0.index in used:
        continue
    loop_edges = []
    e = e0
    # pick a starting vert
    v = e.verts[0]
    guard = 0
    while e.index not in used and guard < 10000:
        used.add(e.index)
        loop_edges.append(e)
        v = e.other_vert(v)
        nxt = None
        for e2 in v.link_edges:
            if e2.is_boundary and e2.index not in used:
                nxt = e2; break
        if nxt is None:
            break
        e = nxt
        guard += 1
    pts = []
    vert_set = set()
    for e in loop_edges:
        for vv in e.verts:
            if vv.index not in vert_set:
                vert_set.add(vv.index)
                pts.append(src(vv.co))
    if len(pts) < 3:
        continue
    cx = sum(p.x for p in pts)/len(pts)
    cy = sum(p.y for p in pts)/len(pts)
    cz = sum(p.z for p in pts)/len(pts)
    rs = [math.hypot(p.x, p.z - AXIS_Z) for p in pts]
    # bore-like if center near axis and r small
    center_r = math.hypot(cx, cz - AXIS_Z)
    loops.append({
        'edges': len(loop_edges),
        'verts': len(pts),
        'center': [round(cx, 4), round(cy, 4), round(cz, 4)],
        'center_r': round(center_r, 4),
        'r_mean': round(sum(rs)/len(rs), 4),
        'r_min': round(min(rs), 4),
        'r_max': round(max(rs), 4),
        'x': [round(min(p.x for p in pts), 4), round(max(p.x for p in pts), 4)],
        'y': [round(min(p.y for p in pts), 4), round(max(p.y for p in pts), 4)],
        'z': [round(min(p.z for p in pts), 4), round(max(p.z for p in pts), 4)],
        'bore_like': center_r < 0.012 and max(rs) < 0.026,
    })

loops.sort(key=lambda L: -L['edges'])
nonbore = [L for L in loops if not L['bore_like']]
result = {'total_loops': len(loops), 'nonbore_loops': len(nonbore),
          'top_nonbore': nonbore[:15], 'top_all': loops[:10]}
(OUT / 'a762_body_loops.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('A762_BODY_LOOPS', json.dumps(result), flush=True)
bm.free()
