"""Inspect AKM body topology vs A762; apply bottomseal-quality fix to A762 editable if openings match."""
import bpy, bmesh, json, math, shutil
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z, R_IN = 0.1024, 0.0200

def body_stats(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    body = bpy.data.objects.get('PSO_ScopeBody')
    if not body:
        return {'error': 'no body', 'meshes': [o.name for o in bpy.data.objects if o.type=='MESH']}
    mw = body.matrix_world
    verts = [(mw @ v.co) - DELTA for v in body.data.vertices]
    faces = [tuple(p.vertices) for p in body.data.polygons]
    tree = BVHTree.FromPolygons(verts, faces)
    # under pierce
    target = Vector((0.0, -0.04, 0.10))
    cam_loc = target + Vector((0.12, -0.05, -0.22))
    direction = (target - cam_loc).normalized()
    z_axis = -direction
    x_axis = z_axis.cross(Vector((0,0,1))); x_axis.normalize()
    y_axis = z_axis.cross(x_axis).normalized()
    half_w, half_h, steps = 0.22, 0.14, 90
    pierce = 0
    for iy in range(steps):
        for ix in range(steps):
            u=(ix/(steps-1))*2-1; v=(iy/(steps-1))*2-1
            dir_w=(direction+x_axis*(u*half_w)+y_axis*(v*half_h)).normalized()
            if tree.ray_cast(cam_loc, dir_w, 0.9)[0] is not None: continue
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
            A=dx*dx+dz*dz; B=2*(ox*dx+oz*dz); C=ox*ox+oz*oz-R_IN*R_IN
            disc=B*B-4*A*C
            if A<1e-12 or disc<0: continue
            sd=math.sqrt(disc)
            ts=[t for t in [(-B-sd)/(2*A),(-B+sd)/(2*A)] if t>0.01]
            if not ts: continue
            t=min(ts)
            if tree.ray_cast(cam_loc, dir_w, t-1e-4)[0] is None:
                pierce += 1
    # boundary
    bm=bmesh.new(); bm.from_mesh(body.data)
    be=sum(1 for e in bm.edges if e.is_boundary)
    bm.free()
    return {
        'v': len(body.data.vertices), 'f': len(body.data.polygons),
        'boundary': be, 'pierce': pierce,
        'has_mount': 'PSO_ScopeMount' in bpy.data.objects,
        'meshes': [o.name for o in bpy.data.objects if o.type=='MESH'],
    }

rep = {
    'A762': body_stats(O/'PSO1_A762_Editable.blend'),
    'AKM': body_stats(O/'PSO1_AKM_Editable.blend'),
    'A762_before_tuck': body_stats(OUT/'PSO1_A762_Editable.before-tuck.blend'),
}
(OUT/'a762_akm_compare.json').write_text(json.dumps(rep, indent=2), encoding='utf-8')
print(json.dumps(rep, indent=2), flush=True)
