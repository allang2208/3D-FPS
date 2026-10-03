"""Find body open loops at the central-housing to eyepiece transition."""
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
bm = bmesh.new(); bm.from_mesh(body.data); bm.edges.ensure_lookup_table()

def src(co):
    return (mw @ co) - DELTA

used=set(); loops=[]
for e0 in [e for e in bm.edges if e.is_boundary]:
    if e0.index in used: continue
    loop=[]; e=e0; v=e.verts[0]
    while e.index not in used:
        used.add(e.index); loop.append(e); v=e.other_vert(v)
        nxt=None
        for e2 in v.link_edges:
            if e2.is_boundary and e2.index not in used:
                nxt=e2; break
        if not nxt: break
        e=nxt
    pts=[src(vv.co) for ed in loop for vv in ed.verts]
    if len(pts)<6: continue
    cx=sum(p.x for p in pts)/len(pts); cy=sum(p.y for p in pts)/len(pts); cz=sum(p.z for p in pts)/len(pts)
    rs=[math.hypot(p.x,p.z-AXIS_Z) for p in pts]
    if -0.03 <= cy <= 0.10:
        loops.append({'n':len(loop),'c':[round(cx,4),round(cy,4),round(cz,4)],
                      'cr':round(math.hypot(cx,cz-AXIS_Z),4),
                      'r':[round(min(rs),4),round(max(rs),4)],
                      'y':[round(min(p.y for p in pts),4),round(max(p.y for p in pts),4)],
                      'z':[round(min(p.z for p in pts),4),round(max(p.z for p in pts),4)],
                      'x':[round(min(p.x for p in pts),4),round(max(p.x for p in pts),4)],
                      'bore': math.hypot(cx,cz-AXIS_Z)<0.012 and max(rs)<0.026})

loops.sort(key=lambda L: -L['n'])
nonbore=[L for L in loops if not L['bore']]
# Also locate the rivet plate by finding a flat cluster of faces with 4 circular features — approximate by faces near [-0.0?, y, z high]
result={'transition_nonbore': nonbore[:20], 'transition_all_top': loops[:12]}
(OUT/'a762_transition_loops.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('TRANSITION', json.dumps(result), flush=True)
bm.free()
