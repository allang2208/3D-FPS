"""Targeted offline optical-ray diagnosis of the installed M249 assembly."""
import bpy,json,pickle,math
import numpy as np
from pathlib import Path
from collections import Counter
from mathutils import Vector,Quaternion
from mathutils.bvhtree import BVHTree
r=Path(__file__).resolve().parent
d=pickle.load(open(r.parent/'Repair13/native.pkl','rb'))
inputs=json.loads((r/'inputs.json').read_text())
recipe=json.loads((r.parent/'Repair12/optic_recipe.json').read_text())
def matrix(v):
    m=np.eye(4);m[:3,:3]=np.array(Quaternion((v[6],*v[3:6])).to_matrix())*v[7:];m[:3,3]=v[:3];return m
def xf(v,m):return np.asarray(v)@m[:3,:3].T+m[:3,3]
def mount(a):return matrix([*a['position'],*a['rotation_xyzw'],*a['scale']])
cover=matrix(d['bind'][d['names'].index('PKM_Cover')])
native=np.array(d['vertices']);native_faces=np.array(d['faces']);section=np.array(d['sections'])
hidden={'M249_OpticalHousing','M249_MagnifierGlass','M249_MagnifierReticle','M249_Bipod'}
visible=[i for i,s in enumerate(d['slots']) if s not in hidden and '__New' not in s]
keep=np.isin(section,visible)
native_faces=native_faces[keep];native_names=[d['slots'][i] for i in section[keep]]
models={}
for key,row in inputs['meshes'].items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=row['fbx'])
    vv=[];ff=[];ss=[]
    slot_by_material={s['material'].rsplit('.',1)[-1]:s['slot'] for s in row['slots']}
    for o in bpy.context.scene.objects:
        if o.type!='MESH':continue
        off=len(vv);o.data.calc_loop_triangles()
        vv.extend([(o.matrix_world@v.co)[:] for v in o.data.vertices])
        for f in o.data.loop_triangles:
            ff.append(tuple(i+off for i in f.vertices))
            mat=o.data.materials[f.material_index].name
            ss.append(slot_by_material.get(mat,mat))
    verts=np.asarray(vv)*[100,-100,100]
    models[key]=(verts,np.asarray(ff),ss)
out={'cases':{},'note':'Bind assembly ray diagnosis; not a gameplay render or acceptance.'}
for key in ('lpvo_1_6x','kv_scope_4x','prism_scope_2x','thermal_scope'):
    row=inputs['meshes'][key];a=cover@mount(recipe['assets'][key]['mount']);inv=np.linalg.inv(a)
    vv,ff,ss=models[key]
    vertices=list(vv);faces=list(ff);names=list(ss)
    off=len(vertices);vertices.extend(xf(native,inv));faces.extend(native_faces+off);names.extend(native_names)
    if recipe['assets'][key]['seat']:
        rv,rf,rs=models['CommonRail'];rail=inv@cover@mount(recipe['rail']['mount'])
        off=len(vertices);vertices.extend(xf(rv,rail));faces.extend(rf+off);names.extend(rs)
    if key=='lpvo_1_6x':
        rv,rf,rs=models['lpvo_ring'];off=len(vertices)
        vertices.extend(rv+np.array(row['sockets']['ZoomRing']['location']));faces.extend(rf+off);names.extend(rs)
    vertices=np.asarray(vertices);faces=np.asarray(faces)
    glass='LPVO_Glass' if key=='lpvo_1_6x' else 'att_lens_scope' if key=='kv_scope_4x' else 'Scope2X_Glass' if key=='prism_scope_2x' else 'Thermal_Display'
    gmask=np.array([s==glass for s in names]);omask=np.array([s!=glass and 'Reticle' not in s for s in names])
    gbvh=BVHTree.FromPolygons(vertices.tolist(),faces[gmask].tolist(),all_triangles=True)
    obvh=BVHTree.FromPolygons(vertices.tolist(),faces[omask].tolist(),all_triangles=True)
    onames=np.array(names)[omask]
    rear=np.array(row['sockets']['SightRear']['location']);front=np.array(row['sockets']['SightFront']['location'])
    forward=(front-rear)/np.linalg.norm(front-rear);up=np.array(row['sockets']['SightUp']['location'])-rear
    side=np.cross(up,forward);side/=np.linalg.norm(side);up=np.cross(forward,side)
    eye=rear-forward*(28 if key=='lpvo_1_6x' else 20)
    rad=1.79 if key=='lpvo_1_6x' else 1.98 if key=='kv_scope_4x' else 1.585 if key=='prism_scope_2x' else 1.4
    hits=Counter();samples=0;missing=0;center=None
    for y in range(-20,21):
        for z in range(-20,21):
            if y*y+z*z>20*20:continue
            aim=rear+side*(y/20*rad*.90)+up*(z/20*rad*.90)
            ray=Vector(aim-eye).normalized();gl,_,_,gd=gbvh.ray_cast(Vector(eye),ray,100)
            ol,_,oi,od=obvh.ray_cast(Vector(eye),ray,100)
            samples+=1
            if gl is None:missing+=1
            if ol is not None and (gl is None or od<gd-.01):hits[str(onames[oi])]+=1
            if y==z==0:center=dict(glass=list(gl) if gl else None,opaque=list(ol) if ol else None,blocker=str(onames[oi]) if ol and (gl is None or od<gd-.01) else None)
    out['cases'][key]=dict(samples=samples,blocked=dict(hits),missing_glass=missing,center=center,
        mesh_bounds_cm=[vv.min(0).tolist(),vv.max(0).tolist()],glass_material=glass,glass_triangles=int(gmask.sum()))
(r/'aperture_trace.json').write_text(json.dumps(out,indent=2))
print('M249_APERTURE_TRACE',json.dumps(out),flush=True)
