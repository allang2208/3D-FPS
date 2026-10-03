"""Dump non-bore boundary loops on mount-side housing; pick rectangular cutout candidates."""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z = 0.1024

bpy.ops.wm.open_mainfile(filepath=str(OUT / 'PSO1_A762_Editable.before-tuck.blend'))
body = bpy.data.objects['PSO_ScopeBody']
mw = body.matrix_world
bm = bmesh.new(); bm.from_mesh(body.data)
bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table()
for v in bm.verts:
    v.co = (mw @ v.co) - DELTA

used=set(); loops=[]
for e0 in bm.edges:
    if not e0.is_boundary or e0.index in used:
        continue
    loop=[]; e=e0; v=e.verts[0]; guard=0
    while e.index not in used and guard<20000:
        used.add(e.index); loop.append(e); v=e.other_vert(v); guard+=1
        nxt=None
        for e2 in v.link_edges:
            if e2.is_boundary and e2.index not in used:
                nxt=e2; break
        if nxt is None: break
        e=nxt
    if len(loop)<10: continue
    # unique verts ordered
    rem=set(loop); e=loop[0]
    ordered=[e.verts[0], e.verts[1]]; rem.remove(e)
    while rem:
        end=ordered[-1]; found=None
        for e2 in list(rem):
            if end in e2.verts:
                found=e2; break
        if not found: break
        rem.remove(found); ordered.append(found.other_vert(end))
    if ordered and ordered[0]==ordered[-1]:
        ordered=ordered[:-1]
    pts=[v.co.copy() for v in ordered]
    if len(pts)<10: continue
    cx=sum(p.x for p in pts)/len(pts)
    cy=sum(p.y for p in pts)/len(pts)
    cz=sum(p.z for p in pts)/len(pts)
    rs=[math.hypot(p.x,p.z-AXIS_Z) for p in pts]
    xs=[p.x for p in pts]; ys=[p.y for p in pts]; zs=[p.z for p in pts]
    cr=math.hypot(cx,cz-AXIS_Z)
    bore = cr<0.012 and max(rs)<0.026
    # planar-ish score: variance of coordinates along least axis
    span_x=max(xs)-min(xs); span_y=max(ys)-min(ys); span_z=max(zs)-min(zs)
    loops.append({
        'n': len(loop), 'bore': bore, 'cr': round(cr,4),
        'c':[round(cx,4),round(cy,4),round(cz,4)],
        'r':[round(min(rs),4),round(max(rs),4)],
        'x':[round(min(xs),4),round(max(xs),4)],
        'y':[round(min(ys),4),round(max(ys),4)],
        'z':[round(min(zs),4),round(max(zs),4)],
        'spans':[round(span_x,4),round(span_y,4),round(span_z,4)],
    })

# Candidates: non-bore, on +X mount side, spans suggest rectangle (two axes large)
cands=[]
for L in loops:
    if L['bore']: continue
    if L['c'][0] < -0.01: continue  # prefer +X / center
    if L['y'][1] < -0.12 or L['y'][0] > 0.08: continue
    # must not be tiny
    if L['n'] < 12: continue
    cands.append(L)
cands.sort(key=lambda L: (-L['n'], L['cr']))

# Also specifically look for loops with significant r span (cutout walls from tube to housing)
wallish=[L for L in cands if L['r'][1]-L['r'][0] > 0.015]
wallish.sort(key=lambda L: -(L['r'][1]-L['r'][0]))

report={'total_loops':len(loops),'nonbore_cands':cands[:25],'wallish':wallish[:15]}
(OUT/'a762_rect_candidates.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('RECT_CAND', json.dumps({'n':len(cands),'top':cands[:8],'wallish':wallish[:6]}), flush=True)
bm.free()
