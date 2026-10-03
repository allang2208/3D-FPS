"""Isolate outer-shell opening rim edges; dump and render rim as thick markers."""
import bpy, bmesh, json, math
from pathlib import Path
from mathutils import Vector

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z = 0.1024

bpy.ops.wm.open_mainfile(filepath=str(OUT / 'PSO1_A762_Editable.before-tuck.blend'))
scene = bpy.context.scene
body = bpy.data.objects['PSO_ScopeBody']
mw = body.matrix_world.copy(); inv = mw.inverted()
bm = bmesh.new(); bm.from_mesh(body.data)
bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()
for v in bm.verts:
    v.co = (mw @ v.co) - DELTA

def rad(co):
    return math.hypot(co.x, co.z - AXIS_Z)

# Outer-shell opening rim: boundary edge whose face is outer (r>0.024) and mid is in ROI
rim = []
for e in bm.edges:
    if not e.is_boundary:
        continue
    mid = (e.verts[0].co + e.verts[1].co) * 0.5
    if not (-0.100 < mid.y < 0.040):
        continue
    if mid.z > 0.135:  # skip turret tops
        continue
    f = e.link_faces[0]
    fc = f.calc_center_median()
    fr = rad(fc)
    mr = rad(mid)
    # outer shell face OR mid on outer band
    if fr < 0.0235 and mr < 0.0235:
        continue  # pure tube rim / bore
    if fr > 0.070 and mid.x < 0.005:
        continue  # far feet
    # mount-side / underside opening
    if mid.x < -0.035:
        continue
    rim.append(e)

# loops
used=set(); loops=[]
for e0 in rim:
    if e0.index in used: continue
    loop=[]; e=e0; v=e.verts[0]; g=0
    while e.index not in used and g<20000:
        used.add(e.index); loop.append(e); v=e.other_vert(v); g+=1
        nxt=None
        for e2 in v.link_edges:
            if e2 in rim and e2.index not in used:
                nxt=e2; break
        if nxt is None: break
        e=nxt
    if len(loop)<8: continue
    pts=[]
    for e in loop:
        pts += [e.verts[0].co, e.verts[1].co]
    cx=sum(p.x for p in pts)/len(pts); cy=sum(p.y for p in pts)/len(pts); cz=sum(p.z for p in pts)/len(pts)
    rs=[rad(p) for p in pts]
    loops.append({
        'n': len(loop),
        'c':[round(cx,4),round(cy,4),round(cz,4)],
        'cr':round(rad(Vector((cx,cy,cz))),4),
        'r':[round(min(rs),4),round(max(rs),4)],
        'y':[round(min(p.y for p in pts),4),round(max(p.y for p in pts),4)],
        'x':[round(min(p.x for p in pts),4),round(max(p.x for p in pts),4)],
        'z':[round(min(p.z for p in pts),4),round(max(p.z for p in pts),4)],
        'edge_indices': [e.index for e in loop],
    })
loops.sort(key=lambda L:-L['n'])

# Create marker object: small icospheres at rim edge midpoints of top 3 loops
marker_me = bpy.data.meshes.new('RimMarkers')
marker_ob = bpy.data.objects.new('RimMarkers', marker_me)
scene.collection.objects.link(marker_ob)
# build combined bmesh of icospheres - simpler: just verts + edges as a polyline mesh
mb = bmesh.new()
colors_loops = loops[:5]
all_verts_co = []
for Li, L in enumerate(colors_loops):
    for ei in L['edge_indices']:
        e = bm.edges[ei]
        mid = (e.verts[0].co + e.verts[1].co) * 0.5
        # marker as tiny tetra around mid
        s = 0.0015
        base = [mb.verts.new(mid + Vector(d)) for d in [
            (s,0,0), (-s,0,0), (0,s,0), (0,0,s)]]
        try:
            mb.faces.new(base[:3]); mb.faces.new([base[0],base[1],base[3]])
            mb.faces.new([base[1],base[2],base[3]]); mb.faces.new([base[2],base[0],base[3]])
        except ValueError:
            pass
        all_verts_co.append(mid)
for v in mb.verts:
    v.co = inv @ (v.co + DELTA)
mb.to_mesh(marker_me); mb.free()
mat = bpy.data.materials.new('RimYellow')
mat.diffuse_color = (1.0, 0.9, 0.1, 1.0)
marker_ob.data.materials.append(mat)

# restore body coords
for v in bm.verts:
    v.co = inv @ (v.co + DELTA)
bm.free()

report = {'rim_edges': len(rim), 'loops': [{k:v for k,v in L.items() if k!='edge_indices'} for L in loops[:10]]}
(OUT/'a762_outer_rim.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

for ob in scene.objects:
    if ob.type == 'MESH':
        keep = ob.name in ('PSO_ScopeBody', 'PSO_ScopeMount', 'PSO_ScopeLens', 'RimMarkers')
        ob.hide_render = not keep; ob.hide_set(not keep)
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = 1700; scene.render.resolution_y = 1100
sh = scene.display.shading
sh.light = 'STUDIO'; sh.color_type = 'MATERIAL'
sh.show_backface_culling = True; sh.show_cavity = True; sh.cavity_type = 'BOTH'
for o in list(scene.objects):
    if o.type=='CAMERA':
        bpy.data.objects.remove(o, do_unlink=True)
cam = bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
scene.collection.objects.link(cam); scene.camera = cam; cam.data.lens = 70
target = DELTA + Vector((0.01, -0.04, 0.09))
for name, off, hide_m in [
    ('outrim_under', Vector((0.12, -0.05, -0.22)), False),
    ('outrim_bodyonly_under', Vector((0.12, -0.05, -0.22)), True),
    ('outrim_side', Vector((0.30, 0.0, 0.03)), False),
    ('outrim_tq', Vector((0.22, -0.22, 0.12)), True),
]:
    if 'PSO_ScopeMount' in bpy.data.objects:
        bpy.data.objects['PSO_ScopeMount'].hide_render = hide_m
    if 'PSO_ScopeLens' in bpy.data.objects:
        bpy.data.objects['PSO_ScopeLens'].hide_render = hide_m
    cam.location = target + off
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(OUT / ('A762_%s.png' % name))
    bpy.ops.render.render(write_still=True)

print('OUTERRIM', json.dumps({'rim':len(rim),'loops':report['loops'][:5]}), flush=True)
