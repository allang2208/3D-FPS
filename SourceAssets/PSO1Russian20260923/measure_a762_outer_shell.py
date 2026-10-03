"""Locate outer-housing shell gaps (beyond thin tube) on pristine A762 body."""
import bpy, bmesh, json, math
from pathlib import Path
from collections import defaultdict
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z = 0.1024

bpy.ops.wm.open_mainfile(filepath=str(OUT / 'PSO1_A762_Editable.before-tuck.blend'))
body = bpy.data.objects['PSO_ScopeBody']
mw = body.matrix_world
verts = [(mw @ v.co) - DELTA for v in body.data.vertices]
faces = [tuple(p.vertices) for p in body.data.polygons]
tree = BVHTree.FromPolygons(verts, faces)

# Sample at several shell radii
results = {}
for R in (0.024, 0.028, 0.032, 0.036, 0.040, 0.045):
    ys = [round(-0.100 + i*0.004, 4) for i in range(40)]
    angs = list(range(-160, 80, 5))
    gaps = []
    for y in ys:
        for ad in angs:
            a = math.radians(ad)
            ox, oz = math.cos(a), math.sin(a)
            start = Vector((1.6*R*ox, y, AXIS_Z + 1.6*R*oz))
            h = tree.ray_cast(start, Vector((-ox,0,-oz)), 1.3*R)
            bad = False
            if h[0] is None:
                bad = True; kind='miss'
            else:
                hit=h[0]; hx,hz=hit.x,hit.z-AXIS_Z; hr=math.hypot(hx,hz)
                same=(hx*ox+hz*oz)>0
                # near-wall at this R band: expect hit near R
                if (not same) or hr < R*0.75 or hr > R*1.25:
                    bad = True; kind = 'opp' if not same else ('deep' if hr < R*0.75 else 'outr')
                else:
                    kind='ok'
            if bad:
                gaps.append({'y':y,'ang':ad,'kind':kind})
    bins=defaultdict(int)
    for g in gaps:
        bins[(round(g['y']/0.02)*0.02, round(g['ang']/20)*20)] += 1
    top=sorted(({'y':k[0],'ang':k[1],'n':n} for k,n in bins.items()), key=lambda d:-d['n'])[:8]
    ys_g=[g['y'] for g in gaps]; angs_g=[g['ang'] for g in gaps]
    results[str(R)] = {
        'gaps': len(gaps),
        'extent': {'y':[min(ys_g),max(ys_g)], 'ang':[min(angs_g),max(angs_g)]} if gaps else None,
        'top': top,
    }

# Boundary loops on outer shell: faces with center r in [0.026, 0.055]
bm=bmesh.new(); bm.from_mesh(body.data)
bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()
for v in bm.verts:
    v.co=(mw@v.co)-DELTA

outer_face = set()
for f in bm.faces:
    c=f.calc_center_median()
    r=math.hypot(c.x,c.z-AXIS_Z)
    if 0.026 <= r <= 0.055 and -0.11 < c.y < 0.05 and c.z < 0.14:
        outer_face.add(f)

# boundary edges of outer_face region (edge with exactly one outer face)
region_bound=[]
for e in bm.edges:
    ofs=[f for f in e.link_faces if f in outer_face]
    if len(ofs)==1 and (e.is_boundary or len(e.link_faces)==2):
        # also include true boundary
        if e.is_boundary or len([f for f in e.link_faces if f not in outer_face])>=1:
            mid=(e.verts[0].co+e.verts[1].co)*0.5
            if -0.11 < mid.y < 0.05:
                region_bound.append(e)

# walk loops among region_bound + true boundary in ROI
bedges=set(region_bound)
for e in bm.edges:
    if e.is_boundary:
        mid=(e.verts[0].co+e.verts[1].co)*0.5
        r=math.hypot(mid.x,mid.z-AXIS_Z)
        if 0.022 <= r <= 0.060 and -0.11 < mid.y < 0.05 and mid.x > -0.02:
            bedges.add(e)

used=set(); loops=[]
for e0 in bedges:
    if e0.index in used: continue
    loop=[]; e=e0; v=e.verts[0]; guard=0
    while e.index not in used and guard<20000:
        used.add(e.index); loop.append(e); v=e.other_vert(v); guard+=1
        nxt=None
        for e2 in v.link_edges:
            if e2 in bedges and e2.index not in used:
                nxt=e2; break
        if nxt is None: break
        e=nxt
    if len(loop)<12: continue
    pts=[]
    for e in loop:
        pts.extend([e.verts[0].co,e.verts[1].co])
    cx=sum(p.x for p in pts)/len(pts); cy=sum(p.y for p in pts)/len(pts); cz=sum(p.z for p in pts)/len(pts)
    rs=[math.hypot(p.x,p.z-AXIS_Z) for p in pts]
    loops.append({
        'n':len(loop),'c':[round(cx,4),round(cy,4),round(cz,4)],
        'cr':round(math.hypot(cx,cz-AXIS_Z),4),
        'r':[round(min(rs),4),round(max(rs),4)],
        'y':[round(min(p.y for p in pts),4),round(max(p.y for p in pts),4)],
        'x':[round(min(p.x for p in pts),4),round(max(p.x for p in pts),4)],
        'z':[round(min(p.z for p in pts),4),round(max(p.z for p in pts),4)],
    })
loops.sort(key=lambda L:-L['n'])

report={'radii':results,'outer_faces':len(outer_face),'region_bound_edges':len(region_bound),
        'bedges':len(bedges),'loops_top':loops[:15]}
(OUT/'a762_outer_shell_gaps.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('OUTER', json.dumps({
    'radii_gaps': {k:v['gaps'] for k,v in results.items()},
    'R028_top': results['0.028']['top'][:5],
    'R036_top': results['0.036']['top'][:5],
    'loops': loops[:6],
}), flush=True)
bm.free()
