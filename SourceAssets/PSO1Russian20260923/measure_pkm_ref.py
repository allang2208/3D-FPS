"""Render PKM ScopeBody underside for reference of sealed look; measure its under pierce."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
AXIS_Z, R = 0.1024, 0.0200

bpy.ops.wm.open_mainfile(filepath=str(O / 'PSO1_PKM_Editable.blend'))
scene = bpy.context.scene
print('PKM_OBJECTS', [o.name for o in scene.objects if o.type=='MESH'], flush=True)
body = bpy.data.objects.get('PSO_ScopeBody')
if not body:
    # try any mesh
    for o in scene.objects:
        if o.type=='MESH':
            print('MESH', o.name, 'v', len(o.data.vertices), 'f', len(o.data.polygons), flush=True)
    raise SystemExit('no PSO_ScopeBody')

# PKM may use different delta - try to detect from object location
print('BODY_LOC', list(body.location), 'v', len(body.data.vertices), 'f', len(body.data.polygons), flush=True)
mw = body.matrix_world
# Use body bbox center as target
verts_w = [mw @ v.co for v in body.data.vertices]
cx = sum(v.x for v in verts_w)/len(verts_w)
cy = sum(v.y for v in verts_w)/len(verts_w)
cz = sum(v.z for v in verts_w)/len(verts_w)
print('BODY_CENTER', round(cx,4), round(cy,4), round(cz,4), flush=True)

for ob in scene.objects:
    if ob.type=='MESH':
        keep = 'Scope' in ob.name or 'PSO' in ob.name or ob==body
        ob.hide_render = not keep; ob.hide_set(not keep)
scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=1700; scene.render.resolution_y=1100
sh=scene.display.shading
sh.light='STUDIO'; sh.color_type='MATERIAL'
sh.show_backface_culling=True; sh.show_cavity=True; sh.cavity_type='BOTH'
for o in list(scene.objects):
    if o.type=='CAMERA':
        bpy.data.objects.remove(o, do_unlink=True)
cam=bpy.data.objects.new('Cam', bpy.data.cameras.new('Cam'))
scene.collection.objects.link(cam); scene.camera=cam; cam.data.lens=70
target=Vector((cx, cy, cz))
for name, off in [
    ('PKM_ref_under', Vector((0.12,-0.05,-0.22))),
    ('PKM_ref_tq', Vector((0.22,-0.22,0.12))),
    ('PKM_ref_side', Vector((0.30,0.0,0.03))),
]:
    cam.location=target+off
    cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/('A762_%s.png'%name))  # keep naming in folder
    bpy.ops.render.render(write_still=True)

# under pierce relative to optical axis guess
# Use AXIS from mean of tube-like verts
DELTA = Vector((cx - 0.0, cy - (-0.04), cz - 0.10))  # rough - better: use known if similar
# Actually PKM authored in same local frame possibly
# Try DELTA same as A762
DELTA = Vector((0.010, -0.015, 0.035))
verts = [(mw @ v.co) - DELTA for v in body.data.vertices]
faces = [tuple(p.vertices) for p in body.data.polygons]
tree = BVHTree.FromPolygons(verts, faces)
target2 = Vector((0.0, -0.04, 0.10))
cam_loc = target2 + Vector((0.12, -0.05, -0.22))
direction = (target2 - cam_loc).normalized()
z_axis=-direction
x_axis=z_axis.cross(Vector((0,0,1))); x_axis.normalize()
y_axis=z_axis.cross(x_axis).normalized()
half_w,half_h,steps=0.22,0.14,90
pierce=0
for iy in range(steps):
    for ix in range(steps):
        u=(ix/(steps-1))*2-1; v=(iy/(steps-1))*2-1
        dir_w=(direction+x_axis*(u*half_w)+y_axis*(v*half_h)).normalized()
        if tree.ray_cast(cam_loc, dir_w, 0.9)[0] is not None:
            continue
        n_hit=0
        for dy in range(-2,3):
            for dx in range(-2,3):
                if dy==0 and dx==0: continue
                if not (0<=iy+dy<steps and 0<=ix+dx<steps): continue
                u2=((ix+dx)/(steps-1))*2-1; v2=((iy+dy)/(steps-1))*2-1
                if tree.ray_cast(cam_loc,(direction+x_axis*(u2*half_w)+y_axis*(v2*half_h)).normalized(),0.9)[0] is not None:
                    n_hit+=1
        if n_hit<10: continue
        ox,oz=cam_loc.x,cam_loc.z-AXIS_Z
        dx,dz=dir_w.x,dir_w.z
        A=dx*dx+dz*dz; B=2*(ox*dx+oz*dz); C=ox*ox+oz*oz-R*R
        disc=B*B-4*A*C
        if A<1e-12 or disc<0: continue
        sd=math.sqrt(disc)
        ts=[t for t in [(-B-sd)/(2*A),(-B+sd)/(2*A)] if t>0.01]
        if not ts: continue
        t=min(ts)
        if tree.ray_cast(cam_loc, dir_w, t-1e-4)[0] is None:
            pierce+=1
print('PKM_UNDER_PIERCE', pierce, flush=True)
